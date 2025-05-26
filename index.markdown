---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: default
---

## Pages

{%assign cover_page = site.pages | where: "number", "cover" %}
{%assign title_page = site.pages | where: "number", "title" %}
{%assign normal_pages = site.pages | reject: "number", "cover" | reject: "number", "title" | sort_natural %}
{%assign sorted_pages = cover_page | concat: title_page | concat: normal_pages %}

{% for page in sorted_pages %}
  {%capture thumb%}/assets/thumbs/cookbook_{{page.number}}_enhanced.png{%endcapture%}
  {% if page.number == "cover" %}
    {%capture thumb%}/assets/thumbs/cookbook_{{page.number}}.png{%endcapture%}
  {%endif%}
  [![]({{thumb | relative_url }})]({{page.url}})
{% endfor %}
