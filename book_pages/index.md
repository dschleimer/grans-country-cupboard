---
layout: page
---

# Pages

{%assign page_groups = site.book_pages | group_by: "chapter" %}
{% for page_group in page_groups %}
  {%assign chapter = site.book_chapters | find: "number", page_group.name %}
### Chapter {{chapter.number}} - [{{chapter.title}}]({{chapter.url}})
{% for page in page_group.items -%}
    <span style="display:inline-block;padding: 10px">
      <span style="display:block">
        [{%- include img.html type="enhanced" id=page.number width = "100" -%}]({{page.url}})
      </span>
      <span style="display:block;text-align: center">
        [{{page.number}}]({{page.url}})
      </span>
    </span>
{%- endfor -%}
{% endfor %}
