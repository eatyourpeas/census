## You're Invited to Complete a Survey

Hi there,

You've been invited to participate in a survey on **{{ brand_title }}**.

### Survey Details

- **Survey Name:** {{ survey_name }}
  {% if organization_name %}- **Organization:** {{ organization_name }}{% endif %}
  {% if end_date %}- **Complete by:** {{ end_date }}{% endif %}

### Your Personal Invite Link

This is a one-time use link created specifically for you:

[**Complete Survey Now**]({{ survey_link }})

Or copy and paste this URL into your browser:

```
{{ survey_link }}
```

### Important Notes

⚠️ **This link can only be used once.** After you submit your response, the link will no longer work.

{% if end_date %}⏰ **Deadline:** Please complete the survey by **{{ end_date }}**.{% endif %}

{% if contact_email %}💬 **Questions?** If you have any questions about this survey, please contact [{{ contact_email }}](mailto:{{ contact_email }}).{% endif %}

---

Thank you for your participation!
{% if organization_name %}{{ organization_name }}{% else %}The {{ brand_title }} Team{% endif %}
