---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: default
---

# Gran's Country Cupboard

{%assign page_groups = site.pages | group_by: "chapter" %}
{% for page_group in page_groups %}
  {%assign chapter = site.chapters | find: "number", page_group.name %}
### Chapter {{chapter.number}} - [{{chapter.title}}]({{chapter.url}})
{% for page in page_group.items -%}
  [{%- include img.html res="thumbs" type="enhanced" id=page.number -%}]({{page.url}})
{%- endfor -%}
{% endfor %}
