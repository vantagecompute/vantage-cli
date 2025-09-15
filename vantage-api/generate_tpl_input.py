import json

import toml

version = toml.load("pyproject.toml")["tool"]["poetry"]["version"]
version = version.replace(".", "_")

# email for inviting people to Vantage
name = f"VantageInviteEmailTemplate-{version}"
subject = "Welcome to Vantage"
html = open("invite_template.html", "r").read()

with open("invite_email.tpl.json", "w") as f:
    json.dump({"Template": {"TemplateName": name, "SubjectPart": subject, "HtmlPart": html}}, f)

# email for notifying people about organization deletion
name = f"VantageDeleteOrgEmailTemplate-{version}"
subject = "Your organization has been deleted"
html = open("delete_org_template.html", "r").read()

with open("delete_org_email.tpl.json", "w") as f:
    json.dump({"Template": {"TemplateName": name, "SubjectPart": subject, "HtmlPart": html}}, f)