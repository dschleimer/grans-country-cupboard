---
title: Categories
layout: default
---

# Browse by Category

{%- assign first_letters = site.categories| where_exp: "r", "1 == 0" -%}
{%- assign titles = site.categories | map: "title" -%}
{%- for title in titles -%}
    {%- assign letter = title | slice: 0 | upcase -%}
    {%- assign first_letters = first_letters | push: letter -%}
{%- endfor -%}
{%- assign first_letters = first_letters | sort| uniq %}

{% for letter in first_letters -%}
    [{{letter}}](#{{letter}}){%- unless forloop.last %} - {% endunless -%}
{%- endfor %}

{% for letter in first_letters %}

<h2 id={{letter}}>{{letter}}</h2>
    {%- for category in site.categories -%}
        {%- assign category_letter = category.title | slice: 0 | upcase -%}
        {%- unless letter == category_letter -%}
            {%- continue -%}
        {%- endunless %}
* [{{category.title}}]({{category.url}})
    {%- endfor -%}
{%- endfor %}