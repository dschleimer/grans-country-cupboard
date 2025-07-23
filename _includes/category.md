# {{page.title}}

{% for recipe in page.recipes -%}
    * [{{recipe.title}}]({{recipe.url | relative_url}})
{% endfor -%}
