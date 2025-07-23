require 'set'

require "jekyll"
require "jekyll/filters"
require "jekyll/document"

module Categories
    class CategoriesGenerator < Jekyll::Generator 
        safe true

        def generate(site)
            book_recipes = site.collections["book_recipes"].docs
            all_categories = Set[]
            for recipe in book_recipes do
                all_categories |= recipe.data.fetch('categories', [])
            end
            generate_category_collection(site, all_categories)
        end

        def generate_category_collection(site, all_categories)
            collection = site.collections["categories"]
            for category in all_categories.to_a.sort do
                slug = Jekyll::Utils.slugify(category)
                path = File.join(site.source, '_categories', "#{slug}.md")
                doc = Jekyll::Document.new(path, {:site => site, :collection => collection})
                recipes = site.collections["book_recipes"].docs.filter {|doc| doc.data['categories'].include?(category)}.sort_by{|doc| doc.data['title'] }

                doc.merge_data!({
                    "title" => category.split().map {|w| w.capitalize}.join(" "),
                    "category" => category,
                    "layout" => "default",
                    "recipes" => recipes,
                })
                doc.content = '{% include category.md %}'
                collection.docs << doc
            end
            collection.docs.sort_by! {|doc| doc.data['category']}
        end
    end
end