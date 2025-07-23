# {{page.title}}
{%include nav_links.md %}

{% for recipe in page.recipes -%}
    * [{{recipe.title}}]({{recipe.url | relative_url}})
{% endfor %}
{%include nav_links.md %}
