require 'set'

require "jekyll"
require "jekyll/filters"

module Ingredients
    class IngredientsGenerator < Jekyll::Generator 
        safe true

        def generate(site)
            book_recipes = site.collections["book_recipes"].docs
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
                    ingredient = cells[1].strip
                    if ingredient.empty? || ingredient == 'Ingredient' || ingredient =~ /^-+$/
                        new_content << line
                        next
                    end
                    # TODO: add some normalization here, e.g. Soft Bread => Bread
                    recipe_ingredients << ingredient
                    slug = Jekyll::Utils.slugify(ingredient)
                    cells[1] = " [#{ingredient}](/ingredients/#{slug}.html) "
                    new_content.append(cells.join('|'))
                end
                tags = recipe_ingredients.map!{|i| "__ingredient:#{i}"}.to_a
                recipe.data["tags"] = recipe.data.fetch("tags", []) + tags
                recipe.content = new_content.join()
            end
        end

    end
end