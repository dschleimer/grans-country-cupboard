{%unless page.number == "cover" %}
    {%assign type = "enhanced" %}
{%else%}
    {%assign type = "original" %}
{%endunless%}

{%- capture recipe_filter -%}doc.collection == "book_recipes" and doc.page == "{{page.number}}"{%- endcapture -%}
{%-assign recipes = site.documents | where_exp: "doc", recipe_filter -%}

{%- capture chapter_filter -%}doc.collection == "book_chapters" and doc.number == {{page.chapter}}{%- endcapture -%}
{%-assign parent_chapter = site.documents | where_exp: "doc", chapter_filter | first -%}

{% include nav_links.md parent=parent_chapter %}<br/>
{%- for recipe in recipes -%}
    <span style="display:inline-block;padding: 10px">
      <span style="display:block;text-align: center">
        [{%- include img.html res="thumbs" type="recipe_crops" id=recipe.recipe width="100" -%}]({{recipe.url}})
      </span>
      <span style="display:block;text-align: center">
        [{{recipe.title}}]({{recipe.url}})
      </span>
    </span>
{%- endfor -%}
<br />
{% include img.html res="web" type="enhanced" id=page.number width="800" %}
<br/>
{% include asset_link.html type="original" id=page.number -%} | {%- include asset_link.html res="full_res" type="enhanced" id=page.number -%}
<br/>
{% include nav_links.md parent=parent_chapter %}<br/>
