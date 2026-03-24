require 'set'
require 'yaml'

require "jekyll"
require "jekyll/filters"
require "jekyll/document"

module Ingredients
    class IngredientsGenerator < Jekyll::Generator
        safe true

        def generate(site)
            @taxonomy = load_taxonomy(site)
            @mappings = load_mappings(site)
            load_modifiers(site)
            @canonical_set, @canonical_to_aisle, @canonical_to_parent,
                @see_also_map, @canonical_variations = flatten_taxonomy(@taxonomy)

            book_recipes = site.collections["book_recipes"].docs
            all_ingredients = extract_tag_and_link_recipes(book_recipes)
            generate_ingredient_collection(site, all_ingredients)
        end

        # -----------------------------------------------------------------
        # Taxonomy & mappings loading
        # -----------------------------------------------------------------

        def load_taxonomy(site)
            path = File.join(site.source, '_data', 'ingredient_taxonomy.yml')
            return {} unless File.exist?(path)
            YAML.safe_load(File.read(path)) || {}
        end

        def load_mappings(site)
            path = File.join(site.source, '_tools', 'ingredient_mappings.yml')
            return {} unless File.exist?(path)
            raw = YAML.safe_load(File.read(path)) || {}
            # Build case-insensitive lookup: lowercase key => canonical value
            result = {}
            raw.each { |k, v| result[k.downcase] = v if v }
            result
        end

        def load_modifiers(site)
            data = site.data["ingredient_modifiers"] || {}
            @modifier_prefixes = (data["prefixes"] || []).sort_by { |m| -m.length }
            @modifier_suffixes = (data["suffixes"] || []).sort_by { |m| -m.length }
        end

        def flatten_taxonomy(taxonomy)
            all_canonical = Set.new
            canonical_to_aisle = {}
            canonical_to_parent = {}
            see_also_map = {}
            canonical_variations = {}  # canonical => [child variations]

            walk = lambda do |members, aisle, parent|
                members.each do |member|
                    if member.is_a?(String)
                        name = member
                        variations = []
                        see_also = []
                    else
                        name = member["name"]
                        variations = member.fetch("variations", [])
                        see_also = member.fetch("see_also", [])
                    end

                    all_canonical.add(name)
                    canonical_to_aisle[name] = aisle
                    canonical_to_parent[name] = parent
                    see_also_map[name] = see_also unless see_also.empty?

                    child_names = variations.map { |v| v.is_a?(String) ? v : v["name"] }
                    canonical_variations[name] = child_names unless child_names.empty?

                    walk.call(variations, aisle, name) unless variations.empty?
                end
            end

            taxonomy.each do |aisle_name, aisle_data|
                members = aisle_data.fetch("members", [])
                walk.call(members, aisle_name, nil)
            end

            [all_canonical, canonical_to_aisle, canonical_to_parent,
             see_also_map, canonical_variations]
        end

        # -----------------------------------------------------------------
        # Resolution chain
        # -----------------------------------------------------------------

        def title_case(raw)
            parts = raw.split(/[^a-zA-Z0-9_']/)
            result = raw.dup
            parts.each do |part|
                next if part.empty?
                capitalized = part[0].upcase + part[1..]
                result.sub!(
                    /(?<![a-zA-Z0-9_'])#{Regexp.escape(part)}(?![a-zA-Z0-9_'])/,
                    capitalized
                )
            end
            result
        end

        def strip_parentheticals(s)
            s.gsub(/\([^)]+\)/, '').strip
        end

        def normalize_raw(raw)
            strip_parentheticals(title_case(raw))
        end

        def try_singular(name)
            # Try standard English plural stripping
            lower = name.downcase
            if lower.end_with?("ies") && lower.length > 4
                # cherries -> cherry — but only if singular form is canonical
                singular = name[0...-3] + "y"
                @canonical_set.each { |c| return c if c.downcase == singular.downcase }
            end
            if lower.end_with?("es") && lower.length > 3
                singular = name[0...-2]
                @canonical_set.each { |c| return c if c.downcase == singular.downcase }
            end
            if lower.end_with?("s") && lower.length > 2
                singular = name[0...-1]
                @canonical_set.each { |c| return c if c.downcase == singular.downcase }
            end
            # Also try adding "s" (singular -> plural canonical)
            plural = name + "s"
            @canonical_set.each { |c| return c if c.downcase == plural.downcase }
            nil
        end

        def resolve_ingredient(raw)
            normalized = normalize_raw(raw)
            key = normalized.downcase

            # 1. Check mappings (case-insensitive)
            if @mappings.key?(key)
                return @mappings[key]
            end

            # 2. Check if normalized form is already a canonical name
            @canonical_set.each { |c| return c if c.downcase == key }

            # 3. Try plural normalization
            singular_match = try_singular(normalized)
            return singular_match if singular_match

            # 4. Try modifier prefix stripping
            @modifier_prefixes.each do |mod|
                mod_lower = mod.downcase
                if key.start_with?(mod_lower + " ")
                    remainder = normalized[(mod.length + 1)..].strip
                    remainder_key = remainder.downcase
                    return @mappings[remainder_key] if @mappings.key?(remainder_key)
                    @canonical_set.each { |c| return c if c.downcase == remainder_key }
                    singular_match = try_singular(remainder)
                    return singular_match if singular_match
                end
            end

            # 5. Try modifier suffix stripping (e.g., "Cheese - Grated")
            @modifier_suffixes.each do |mod|
                mod_lower = mod.downcase
                [" - ", ", "].each do |sep|
                    suffix = sep + mod_lower
                    if key.end_with?(suffix)
                        remainder = normalized[0...(normalized.length - sep.length - mod.length)].strip
                        remainder_key = remainder.downcase
                        return @mappings[remainder_key] if @mappings.key?(remainder_key)
                        @canonical_set.each { |c| return c if c.downcase == remainder_key }
                        singular_match = try_singular(remainder)
                        return singular_match if singular_match
                    end
                end
            end

            # 6. Unknown — use normalized form as-is
            normalized
        end

        # -----------------------------------------------------------------
        # Recipe extraction & linking
        # -----------------------------------------------------------------

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
                        ingredient_offsets = 1..(cells.size - 2)
                    else
                        ingredient_offsets = 1..1
                    end
                    for i in ingredient_offsets do
                        ingredient = cells[i].strip
                        if ingredient.empty?
                            next
                        end
                        # Title-case for display
                        display_name = title_case(ingredient)
                        # Resolve to canonical name
                        canonical = resolve_ingredient(ingredient)
                        recipe_ingredients << canonical
                        slug = Jekyll::Utils.slugify(canonical)
                        cells[i] = " [#{display_name}](/ingredients/#{slug}.html) "
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

        # -----------------------------------------------------------------
        # Page generation
        # -----------------------------------------------------------------

        def breadcrumb_for(canonical)
            crumbs = []
            aisle = @canonical_to_aisle[canonical]
            parent = @canonical_to_parent[canonical]

            # Walk up the parent chain
            chain = []
            current = parent
            while current
                chain.unshift(current)
                current = @canonical_to_parent[current]
            end

            # Aisle is always the top level
            crumbs << { "name" => aisle, "url" => "/ingredients/index.html" } if aisle

            chain.each do |ancestor|
                slug = Jekyll::Utils.slugify(ancestor)
                crumbs << { "name" => ancestor, "url" => "/ingredients/#{slug}.html" }
            end

            crumbs
        end

        def generate_ingredient_collection(site, all_ingredients)
            collection = site.collections["ingredients"]
            all_recipes = site.collections["book_recipes"].docs

            # Precompute direct recipe count per canonical name
            direct_counts = Hash.new(0)
            all_recipes.each do |recipe|
                (recipe.data['tags'] || []).each do |tag|
                    if tag.start_with?("__ingredient:")
                        name = tag.sub("__ingredient:", "")
                        direct_counts[name] += 1
                    end
                end
            end

            # Compute total recipe count (direct + all descendants) recursively
            total_counts = {}
            count_total = lambda do |name|
                return total_counts[name] if total_counts.key?(name)
                total = direct_counts[name]
                (@canonical_variations[name] || []).each do |child|
                    total += count_total.call(child)
                end
                total_counts[name] = total
                total
            end
            @canonical_set.each { |name| count_total.call(name) }

            # Determine which pages to generate
            all_pages = Set.new(all_ingredients)
            @canonical_set.each do |canonical|
                all_pages.add(canonical) if total_counts.fetch(canonical, 0) > 0
            end

            # Helper: collect all descendant names (including self)
            collect_descendants = lambda do |name|
                result = Set[name]
                (@canonical_variations[name] || []).each do |child|
                    result.merge(collect_descendants.call(child))
                end
                result
            end

            for ingredient in all_pages.to_a.sort do
                slug = Jekyll::Utils.slugify(ingredient)
                path = File.join(site.source, '_ingredients', "#{slug}.md")
                doc = Jekyll::Document.new(path, {:site => site, :collection => collection})

                # Direct recipes (only this ingredient)
                tag = "__ingredient:#{ingredient}"
                recipes = all_recipes
                    .filter {|d| d.data['tags']&.include?(tag)}
                    .sort_by {|d| d.data['title'] }

                # All recipes (this ingredient + all variations, deduplicated)
                descendant_names = collect_descendants.call(ingredient)
                descendant_tags = descendant_names.map { |n| "__ingredient:#{n}" }
                all_ingredient_recipes = all_recipes
                    .filter {|d| (d.data['tags'] || []).any? { |t| descendant_tags.include?(t) }}
                    .sort_by {|d| d.data['title'] }
                    .uniq { |d| d.relative_path }

                # Taxonomy metadata
                aisle = @canonical_to_aisle[ingredient]
                parent = @canonical_to_parent[ingredient]
                see_also = @see_also_map[ingredient] || []
                variations = @canonical_variations[ingredient] || []
                breadcrumbs = breadcrumb_for(ingredient)

                # Build variation data with recipe counts (total, not just direct)
                variation_data = variations.map do |v|
                    v_total = total_counts.fetch(v, 0)
                    v_slug = Jekyll::Utils.slugify(v)
                    v_vars = (@canonical_variations[v] || []).size
                    { "name" => v, "slug" => v_slug, "recipe_count" => v_total,
                      "variation_count" => v_vars,
                      "url" => "/ingredients/#{v_slug}.html" }
                end.select { |v| v["recipe_count"] > 0 || v["variation_count"] > 0 }

                # Build see_also data with slugs
                see_also_data = see_also.map do |sa|
                    sa_slug = Jekyll::Utils.slugify(sa)
                    if @taxonomy.key?(sa)
                        # Link to aisle anchor on index page
                        { "name" => sa, "slug" => sa_slug,
                          "url" => "/ingredients/index.html##{sa_slug}" }
                    else
                        { "name" => sa, "slug" => sa_slug,
                          "url" => "/ingredients/#{sa_slug}.html" }
                    end
                end

                # Parent link
                parent_data = nil
                if parent
                    p_slug = Jekyll::Utils.slugify(parent)
                    parent_data = { "name" => parent, "slug" => p_slug,
                                    "url" => "/ingredients/#{p_slug}.html" }
                end

                doc.merge_data!({
                    "title" => ingredient,
                    "render_with_liquid" => true,
                    "ingredient" => ingredient,
                    "layout" => "page",
                    "recipes" => recipes,
                    "all_recipes" => all_ingredient_recipes,
                    "recipe_count" => total_counts.fetch(ingredient, 0),
                    "direct_recipe_count" => recipes.size,
                    "variation_count" => variation_data.size,
                    "aisle" => aisle,
                    "parent_ingredient" => parent_data,
                    "breadcrumbs" => breadcrumbs,
                    "variations" => variation_data,
                    "see_also" => see_also_data,
                })
                doc.content = '{% include ingredient.md %}'
                collection.docs << doc
            end
            collection.docs.sort_by! {|doc| doc.data['ingredient']}
        end
    end
end
