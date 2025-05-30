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

TODO: these should be grouped by chapter
{% for page in site.pages %}
  {%capture thumb%}/assets/thumbs/cookbook_{{page.number}}_enhanced.png{%endcapture%}
  {% if page.number == "cover" %}
    {%capture thumb%}/assets/thumbs/cookbook_{{page.number}}.png{%endcapture%}
  {%endif%}
  [![]({{thumb | relative_url }})]({{page.url}})
{% endfor %}
