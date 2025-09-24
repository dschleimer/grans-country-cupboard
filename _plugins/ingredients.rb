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
                        ingredient_parts = ingredient.split(/\W+/)
                        for part in ingredient_parts do
                            # this regex uses negative lookahead and lookbehind expressions to only
                            # match a complete copy of word by only matching if that word is neither preceeded
                            # nor followed by a word character
                            ingredient.sub!(/(?<!\w)#{Regexp.escape(part)}(?!\w)/, part.capitalize)
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
            # TODO: add more normalization here, e.g. Soft Bread => Bread
            normalized = ingredient.gsub(/\([^)]+\)/, '')
            normalized.strip!
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