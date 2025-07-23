---
title: Recipes
layout: default
---

# Browse by Recipe

{%- assign first_letters = site.book_recipes| where_exp: "r", "1 == 0" -%}
{%- assign titles = site.book_recipes | map: "title" -%}
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
    {%- for recipe in site.book_recipes -%}
        {%- assign recipe_letter = recipe.title | slice: 0 | upcase -%}
        {%- unless letter == recipe_letter -%}
            {%- continue -%}
        {%- endunless %}
* [{{recipe.title}}]({{recipe.url}})
    {%- endfor -%}
{%- endfor %}