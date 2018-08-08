{% for c in m.all() %}
	=== <div id="{{c.uid()}}">{% if m.config_param is defined %}[{{c.config_url()}} {{m.item_name}}: {{c}}]{% else %}{{m.item_name}}: {{c}}{% endif %}</div> ===
	{% for k,v in c if v.description != "" %}
		{% if v.value is iterable and v.value|length > 0 and v.value[0] is not string %}
			* {{v.description|capfirst}}:
			{% for i in v.value %}
				** {{i}}
			{% endfor %}
		{% elif v.value is iterable and v.value|length == 0 %}
			* {{v.description|capfirst}}: '''<span style='color:#AAAAAA'>(none)</span>'''
		{% else %}
			* {{v.description|capfirst}}: {% if v|string|length == 0 %}'''<span style='color:#AAAAAA'>(empty)</span>'''
			{% else %}'''{{v}}'''
			{% endif %}
		{% endif %}
	{% endfor %}
{% endfor %}
