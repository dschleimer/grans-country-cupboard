{%- assign tag = page.ingredient | prepend: "__ingredient:" -%}

# {{page.title}}

{% assign links = site.book_recipes | where_exp: "f", "0 == 1" -%}
{%- for recipe in site.book_recipes | sort_natural -%}
    {%- if recipe.tags contains tag -%}
        {%- capture l -%}* [{{recipe.title}}]({{recipe.url | relative_url}}){%- endcapture -%}
        {%- assign links = links | push: l -%}
    {%- endif -%}
{%- endfor -%}

{% for l in links | sort -%}
  {{- l }}
{% endfor %}

{{links | escape| inspect }}