---
---

{%unless page.number == "cover" %}
    {%assign type = "enhanced" %}
{%else%}
    {%assign type = "original" %}
{%endunless%}

{%capture web%}/assets/web/{{type}}/{{page.number}}.jpg{%endcapture%}
{%capture orig%}/assets/full_res/original/{{page.number}}.jpg{%endcapture%}
{%capture enhanced%}/assets/full_res/enhanced/{{page.number}}.jpg{%endcapture%}

{%case page.number%}
    {% when "cover" %}
        {%assign next = "title" %}
    {%when  "title" %}
        {%assign next = "001" %}
        {%assign prev = "cover" %}
    {%when "001" %}
        {%assign next = "002" %}
        {%assign prev = "title" %}
    {%when "209" %}
        {%assign prev = "208" %}
    {%else %}
        {%assign numeric_page = page.number | to_integer %}
        {%assign next_num = numeric_page | plus: 1 %}
        {%assign prev_num = numeric_page | minus: 1 %}
        {%assign next = next_num | prepend: '000' | slice: -3, 3 %}
        {%assign prev = prev_num | prepend: '000' | slice: -3, 3 %}
{%endcase %}

{%if prev %}
    {%capture prev_url%}/pages/{{prev}}.html{% endcapture %}
    {%capture prev_link%}[Previous Page]({{prev_url | relative_url}}) | {% endcapture %}
{%endif%}
{%if next %}
    {%capture next_url%}/pages/{{next}}.html{% endcapture %}
    {%capture next_link%} | [Next Page]({{next_url | relative_url}}){% endcapture %}
{%endif%}

{%capture chapter_url %}/chapters/{{page.chapter}}.html{%endcapture %}
{%capture chpater_link %}[Chapter Index]({{chapter_url | relative_url}}){%endcapture %}

{{prev_link}}{{chpater_link}}{{next_link}}
![Page {{page.number}}]({{web | relative_url}})
[Original Full Resolution]({{orig | relative_url}}) | [Enhanced Full Resolution]({{enhanced | relative_url}})<br/>
{{prev_link}}{{chpater_link}}{{next_link}}
