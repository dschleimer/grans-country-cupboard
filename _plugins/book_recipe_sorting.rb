require 'set'

require "jekyll"

module Recipes
    class RecipeSortingGenerator < Jekyll::Generator 
        safe true

        def generate(site)
            site.collections['book_recipes'].docs.sort_by! {|doc| "#{doc.data['page']}/#{doc.data['page_order']}/#{doc.path}"}
        end
    end
end