---
layout: page
---

# Ingredients

{% comment %}Aisle jump links{% endcomment -%}
**Aisles:** {% for aisle in site.data.ingredient_taxonomy -%}
{%- assign aisle_name = aisle[0] -%}
[{{ aisle_name }}](#{{ aisle_name | slugify }}){%- unless forloop.last %} · {% endunless -%}
{%- endfor %}

{% comment %}Alphabetical jump links{% endcomment -%}
{%- assign titles = site.ingredients | map: "title" -%}
{%- assign first_letters = "" | split: "" -%}
{%- for title in titles -%}
    {%- assign letter = title | slice: 0 | upcase -%}
    {%- assign first_letters = first_letters | push: letter -%}
{%- endfor -%}
{%- assign first_letters = first_letters | sort | uniq %}
**A–Z:** {% for letter in first_letters -%}
[{{letter}}](#{{letter}}){%- unless forloop.last %} · {% endunless -%}
{%- endfor %}

---

## Browse by Aisle

{% for aisle in site.data.ingredient_taxonomy -%}
{%- assign aisle_name = aisle[0] -%}
{%- assign aisle_data = aisle[1] -%}

### {{ aisle_name }}

{% for member in aisle_data.members -%}
{%- if member.name -%}
  {%- assign name = member.name -%}
{%- else -%}
  {%- assign name = member -%}
{%- endif -%}
{%- assign slug = name | slugify -%}
{%- assign ing_page = site.ingredients | where: "ingredient", name | first -%}
{%- if ing_page %}
* [{{ name }}](/ingredients/{{ slug }}.html){% if ing_page.recipe_count > 0 or ing_page.variation_count > 0 %} — {% if ing_page.recipe_count > 0 %}{{ ing_page.recipe_count }} recipe{% if ing_page.recipe_count != 1 %}s{% endif %}{% endif %}{% if ing_page.recipe_count > 0 and ing_page.variation_count > 0 %}, {% endif %}{% if ing_page.variation_count > 0 %}{{ ing_page.variation_count }} variation{% if ing_page.variation_count != 1 %}s{% endif %}{% endif %}{% endif %}
{%- else %}
* {{ name }}
{%- endif -%}
{%- endfor %}
{%- if aisle_data.see_also %}

**See also:** {% for sa in aisle_data.see_also -%}
{%- assign sa_slug = sa | slugify -%}
[{{ sa }}](/ingredients/{{ sa_slug }}.html){%- unless forloop.last %}, {% endunless -%}
{%- endfor %}
{%- endif %}

{% endfor %}

---

## All Ingredients (A–Z)

{% include alpha_group_docs.md docs=site.ingredients %}
