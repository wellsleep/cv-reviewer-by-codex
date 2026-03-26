import json

import yaml


class JobRuleDocumentService:
    def to_yaml(self, job_rule):
        return yaml.safe_dump(
            job_rule,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )

    def parse(self, content):
        text = (content or "").strip()
        if not text:
            raise ValueError("rule document cannot be empty")

        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError("invalid YAML/JSON format: {0}".format(exc))

        if not isinstance(parsed, dict):
            raise ValueError("rule document must parse to an object")

        return parsed


job_rule_document_service = JobRuleDocumentService()
