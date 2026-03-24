{%- comment -%}Breadcrumb navigation{%- endcomment -%}
{%- if page.breadcrumbs.size > 0 -%}
{%- for crumb in page.breadcrumbs -%}
[{{ crumb.name }}]({{ crumb.url }}) &rsaquo; {% endfor %}**{{ page.title }}**
{%- endif %}

{%- comment -%}Parent ingredient link (redundant with breadcrumbs, removed){%- endcomment -%}

{%- comment -%}Variations list{%- endcomment -%}
{%- if page.variations.size > 0 %}

### Varieties
{% for v in page.variations -%}
* [{{ v.name }}]({{ v.url }}){% if v.recipe_count > 0 or v.variation_count > 0 %} ({% if v.recipe_count > 0 %}{{ v.recipe_count }} recipe{% if v.recipe_count != 1 %}s{% endif %}{% endif %}{% if v.recipe_count > 0 and v.variation_count > 0 %}, {% endif %}{% if v.variation_count > 0 %}{{ v.variation_count }} variation{% if v.variation_count != 1 %}s{% endif %}{% endif %}){% endif %}
{% endfor -%}
{%- endif %}

{%- comment -%}See also cross-references{%- endcomment -%}
{%- if page.see_also.size > 0 %}

**See also:** {% for sa in page.see_also -%}
[{{ sa.name }}]({{ sa.url }}){%- unless forloop.last %}, {% endunless -%}
{%- endfor %}
{%- endif %}

{%- comment -%}Recipe list{%- endcomment -%}
{%- if page.all_recipes.size > 0 %}

### Recipes ({{ page.all_recipes.size }})

{% include alpha_group_docs.md docs=page.all_recipes %}
{%- endif -%}
