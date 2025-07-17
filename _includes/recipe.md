
{%- capture doc_filter -%}doc.collection == "book_pages" and doc.number == "{{page.page}}"{%- endcapture -%}
{%- assign parent_page = site.documents | where_exp: "doc", doc_filter | first -%}

{% include img.html res="web" type="recipe_crops" id=page.recipe %}
<br />
{% include asset_link.html res="full_res" type="recipe_crops" id=page.recipe %}
<br />
{% include nav_links.md parent=parent_page %}
