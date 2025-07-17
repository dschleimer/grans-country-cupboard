{%- assign category = page.collection | remove_first: "book_" | remove: "s" | capitalize -%}
{%- assign parent_category = include.parent.collection | remove_first: "book_" | remove: "s" | capitalize -%}

{%- if page.previous -%}
    {%-capture prev_link -%}[Previous {{category}}]({{page.previous.url | relative_url }}) | {% endcapture -%}
{%- endif -%}

{%- if page.next -%}
    {%-capture next_link %} | [Next {{category}}]({{page.next.url | relative_url }}){% endcapture -%}
{%- endif -%}

{%- capture parent_link -%}[Up To {{parent_category}}]({{include.parent.url | relative_url}}){%- endcapture -%}

{{prev_link}}{{parent_link}}{{next_link}}