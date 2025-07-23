---
title: Ingredients
layout: default
---

# Browse by Ingredient

{%- assign first_letters = site.ingredients| where_exp: "r", "1 == 0" -%}
{%- assign titles = site.ingredients | map: "title" -%}
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
    {%- for ingredient in site.ingredients -%}
        {%- assign ingredient_letter = ingredient.title | slice: 0 | upcase -%}
        {%- unless letter == ingredient_letter -%}
            {%- continue -%}
        {%- endunless %}
* [{{ingredient.title}}]({{ingredient.url}})
    {%- endfor -%}
{%- endfor %}