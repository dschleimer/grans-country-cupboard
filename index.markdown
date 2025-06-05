---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: default
---

# Gran's Country Cupboard

{%assign page_groups = site.pages | group_by: "chapter" %}
{% for page_group in page_groups %}
  {%assign chapter = site.chapters | find: "number", page_group.name %}
### Chapter {{chapter.number}} - [{{chapter.title}}]({{chapter_path | relative_url}})
  {%for page in page_group.items %}{%capture thumb%}/assets/thumbs/cookbook_{{page.number}}_enhanced.png{%endcapture%}{% if page.number == "cover" %}{%capture thumb%}/assets/thumbs/cookbook_{{page.number}}.png{%endcapture%}{%endif%}[![]({{thumb | relative_url }})]({{page.url}}){% endfor %}
{% endfor %}
