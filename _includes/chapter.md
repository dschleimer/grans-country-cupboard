{%- assign chapter_pages = site.book_pages | where: "chapter", page.number -%}

{%include nav_links.md %}
{% include img.html type="enhanced" id=page.title_page width="800" %}

## Pages
{% for page in chapter_pages -%}
  [{%- include img.html type="enhanced" id=page.number width="100" -%}]({{page.url}})
{%- endfor -%}
<br/>
{%include nav_links.md %}