{%- if page.previous -%}
    {%-capture prev_link -%}[Previous Recipe]({{page.previous.url | relative_url }}) | {% endcapture -%}
{%- endif -%}
{%- if page.next -%}
    {%-capture next_link %} | [Next Recipe]({{page.next.url | relative_url }}){% endcapture -%}
{%- endif -%}
{%- capture page_url-%}/pages/{{page.page}}.html{%- endcapture -%}
{%- capture page_link -%}[Page Index]({{page_url | relative_url}}){%- endcapture -%}

{% include img.html res="web" type="recipe_crops" id=page.recipe %}
<br />
{% include asset_link.html res="full_res" type="recipe_crops" id=page.recipe %}
<br />
{{prev_link}}{{page_link}}{{next_link}}
