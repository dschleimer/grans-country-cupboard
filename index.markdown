---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: default
---

## Pages

{% assign sorted_pages = site.pages | sort_natural %}
{% for page in sorted_pages%}
  {%capture thumb%}/assets/thumbs/cookbook_{{page.number}}_enhanced.png{%endcapture%}
  {% if page.number == "cover" %}
    {%capture thumb%}/assets/thumbs/cookbook_{{page.number}}.png{%endcapture%}
  {%endif%}
  [![]({{thumb | relative_url }})]({{page.url}})
{% endfor %}
