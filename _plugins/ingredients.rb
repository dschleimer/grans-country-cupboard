require 'set'

require "jekyll"
require "jekyll/filters"
require "jekyll/document"

module Ingredients
    class IngredientsGenerator < Jekyll::Generator 
        safe true

        def generate(site)
            book_recipes = site.collections["book_recipes"].docs
            all_ingredients = extract_tag_and_link_recipes(book_recipes)
            generate_ingredient_collection(site, all_ingredients)
        end

        def extract_tag_and_link_recipes(book_recipes)
              all_ingredients = Set[]
            for recipe in book_recipes do
                new_content = []
                recipe_ingredients = Set[]
                for line in recipe.content.lines
                    unless line.start_with?('|')
                        new_content << line
                        next
                    end
                    cells = line.split('|')
                    if cells.size < 2
                        new_content << line
                        next
                    end
                    if cells[1].empty? || cells[1].strip == 'Ingredient' || cells[1].strip =~ /^-+$/
                        new_content << line
                        next
                    end
                    if recipe.relative_path == "_book_recipes/027/danish_style_sandwiches.md"
                        if cells[1].strip == 'Bread'
                            new_content << line
                            next
                        end
                        ingredient_offsets = 1..(cells.size - 2) # the cells array has empty start and end cells
                    else
                        ingredient_offsets = 1..1
                    end
                    for i in ingredient_offsets do 
                        ingredient = cells[i].strip
                        if ingredient.empty?
                            next
                        end
                        # we case-normalize first, because we want the pretty casing in the rendered html
                        # our word-splitting logic is complex to handle cases where words may be
                        # surrounded by a paranthesis on one or both ends, and may also contain an apostrophe in the word
                        # _tools/recipe_stats.py can produce a json histogram of the raw ingredient text, i.e. a list of all the
                        # cases we need to handle
                        ingredient_parts = ingredient.split(/[^a-zA-Z0-9_']/)
                        for part in ingredient_parts do
                            # this regex uses negative lookahead and lookbehind expressions to only
                            # match a complete copy of word by only matching if that word is neither preceeded
                            # nor followed by a word character
                            # # we can't sue the built-in word character classes because we need to treat ' as a word character
                            ingredient.sub!(/(?<![a-zA-Z0-9_'])#{Regexp.escape(part)}(?![a-zA-Z0-9_'])/, part.capitalize)
                        end
                        normalized_ingredient = normalized_ingredient(ingredient)

                        recipe_ingredients << normalized_ingredient
                        slug = Jekyll::Utils.slugify(normalized_ingredient)
                        cells[i] = " [#{ingredient}](/ingredients/#{slug}.html) "
                    end
                    new_content.append(cells.join('|'))
                end
                tags = recipe_ingredients.map {|i| "__ingredient:#{i}"}.to_a
                recipe.data["tags"] = recipe.data.fetch("tags", []) + tags
                recipe.content = new_content.join()
                all_ingredients |= recipe_ingredients
            end
            all_ingredients
        end

        def normalized_ingredient(ingredient)
            # Remove parenthetical text
            normalized = ingredient.gsub(/\([^)]+\)/, '')
            # Strip trailing commas/periods
            normalized.gsub!(/[,.]+$/, '')
            # Replace dash / plus / slash characters with a single space
            #    (includes hyphen, en‑dash, em‑dash)
            normalized.gsub!(/[‑–\-+\/]+/, ' ')
            normalized.strip!

            # 
            normalized.gsub!(/  */, ' ')

            # 7.  Deduplicate common typos / variants
            #    (lookup is case‑insensitive).  The hash values are in the canonical
            #    title‑case we want in the final output.
            typo_corrections = {
              'bread crumbs'           => 'Bread Crumbs',
              'bread crumps'           => 'Bread Crumbs',
              'egg whites'             => 'Egg',
              'egss'                   => 'Egg',
              'pimentos'               => 'Pimento',
              'potatoes'               => 'Potato',
              'worchestershire sauce'  => 'Worcestershire Sauce',
              # add more as needed
            }

            lower = normalized.downcase
            if typo_corrections.key?(lower)
              normalized = typo_corrections[lower]
            end

            # 5.  Singular/Plural normalisation
            #    Only apply to a *single‑word* ingredient that ends with an "s"
            #    and is not in the set of known plural forms.
            #    (This keeps phrases like "Italian Bread Crumbs" untouched.)
            words = normalized.split
            if words.length == 1
              word = words[0]
              # exceptions that must stay plural
              plural_exceptions = Set.new([
                'Bread Crumbs', 'Pimentos', 'Oily', 'Crumbs',
                'Peas', 'Leaves', 'Leaves', 'Rice Chicks', 'Rice Chex'
              ])
              if word.end_with?('s') && !plural_exceptions.include?(word)
                normalized = word[0..-2]          # drop final 's'
              end
            end

            normalized
        end

        def generate_ingredient_collection(site, all_ingredients)
            collection = site.collections["ingredients"]
            for ingredient in all_ingredients.to_a.sort do
                slug = Jekyll::Utils.slugify(ingredient)
                path = File.join(site.source, '_ingredients', "#{slug}.md")
                doc = Jekyll::Document.new(path, {:site => site, :collection => collection})
                tag = "__ingredient:#{ingredient}"
                recipes = site.collections["book_recipes"].docs.filter {|doc| doc.data['tags'].include?(tag)}.sort_by{|doc| doc.data['title'] }

                doc.merge_data!({
                    "title" => ingredient.split().map {|w| w.capitalize}.join(" "),
                    "ingredient" => ingredient,
                    "layout" => "page",
                    "recipes" => recipes,
                })
                doc.content = '{% include ingredient.md %}'
                collection.docs << doc
            end
            collection.docs.sort_by! {|doc| doc.data['ingredient']}
        end
    end
end
