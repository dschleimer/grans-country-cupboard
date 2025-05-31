---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: default
---

## Chapters

{% for chapter in site.chapters %}
  {%capture chapter_path %}/chapters/{{chapter.number}}.html{%endcapture %}
### {{chapter.number}} - [{{chapter.title}}]({{chapter_path | relative_url}})
{% endfor %}

## Pages
{%assign page_groups = site.pages | group_by: "chapter" %}
{% for page_group in page_groups %}
  {%assign chapter = site.chapters | find: "number", page_group.name %}
### Chapter {{page_group.name}} - {{chapter.title}}
  {%for page in page_group.items %}{%capture thumb%}/assets/thumbs/cookbook_{{page.number}}_enhanced.png{%endcapture%}{% if page.number == "cover" %}{%capture thumb%}/assets/thumbs/cookbook_{{page.number}}.png{%endcapture%}{%endif%}[![]({{thumb | relative_url }})]({{page.url}}){% endfor %}
{% endfor %}
