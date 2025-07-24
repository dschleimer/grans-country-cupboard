{%- assign first_letters = include.docs| where_exp: "r", "1 == 0" -%}
{%- assign titles = include.docs | map: "title" -%}
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
    {%- for doc in include.docs -%}
        {%- assign doc_letter = doc.title | slice: 0 | upcase -%}
        {%- unless letter == doc_letter -%}
            {%- continue -%}
        {%- endunless %}
* [{{doc.title}}]({{doc.url}})
    {%- endfor -%}
{%- endfor %}