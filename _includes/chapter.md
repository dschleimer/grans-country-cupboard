---
---

{%capture web%}/assets/web/cookbook_{{page.title_page}}_enhanced.jpg{%endcapture%}

{%assign chapter_pages = site.pages | where: "chapter", page.number %}

![Chapter Header Page]({{web | relative_url}})

## Pages
{% for page in chapter_pages %}{%capture thumb%}/assets/thumbs/cookbook_{{page.number}}_enhanced.png{%endcapture%}{% if page.number == "cover" %}{%capture thumb%}/assets/thumbs/cookbook_{{page.number}}.png{%endcapture%}{%endif%}[![]({{thumb | relative_url }})]({{page.url}}){% endfor %}

