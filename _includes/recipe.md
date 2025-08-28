
{%- capture doc_filter -%}doc.collection == "book_pages" and doc.number == "{{page.page}}"{%- endcapture -%}
{%- assign parent_page = site.documents | where_exp: "doc", doc_filter | first -%}

<br />
{% include nav_links.md parent=parent_page %}

{% github_edit_link "Edit this recipe" %}