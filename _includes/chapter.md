---
---

{%capture web%}/assets/web/enhanced/cookbook_{{page.title_page}}.jpg{%endcapture%}

{%assign chapter_pages = site.pages | where: "chapter", page.number %}

![Chapter Header Page]({{web | relative_url}})

## Pages
{% for page in chapter_pages %}{%capture thumb%}/assets/thumbs/enhanced/cookbook_{{page.number}}.png{%endcapture%}{% if page.number == "cover" %}{%capture thumb%}/assets/thumbs/original/cookbook_{{page.number}}.png{%endcapture%}{%endif%}[![]({{thumb | relative_url }})]({{page.url}}){% endfor %}

