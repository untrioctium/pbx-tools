{| border="1" cellspacing="0" cellpadding="2"
{% for k, f in m.fields.items() if f.description != "" %}
	!{{f.description|capfirst}}
{% endfor %}
|----
{% for c in m.all() %}
	{% for k,v in c %}
		{%if v.description != "" %}|{{v}}
		{% endif %}
	{% endfor %}
	|----
{% endfor %}
|}{{nl}}
