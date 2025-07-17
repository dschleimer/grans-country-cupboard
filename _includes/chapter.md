{%- capture web -%}/assets/web/enhanced/{{page.title_page}}.jpg{%- endcapture -%}

{%- assign chapter_pages = site.pages | where: "chapter", page.number -%}

{%include nav_links.md %}
<br/>
{% include img.html res="web" type="enhanced" id=page.title_page %}

## Pages
{% for page in chapter_pages -%}
  [{%- include img.html res="thumbs" type="enhanced" id=page.number -%}]({{page.url}})
{%- endfor -%}
<br/>
{%include nav_links.md %}