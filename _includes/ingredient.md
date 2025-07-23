{%- assign tag = page.ingredient | prepend: "__ingredient:" -%}

# {{page.title}}
{%include nav_links.md %}

{% assign links = site.book_recipes | where_exp: "f", "0 == 1" -%}
{%- for recipe in page.recipes -%}
    {%- unless recipe.tags contains tag -%}
        {%- continue -%}
    {%- endunless -%}
    * [{{recipe.title}}]({{recipe.url | relative_url}})
{% endfor %}
{%include nav_links.md %}
