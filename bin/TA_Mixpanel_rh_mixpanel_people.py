
import ta_mixpanel_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=3600,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=True,
        encrypted=False,
        default='mixpanel:people',
        validator=validator.String(
            min_len=0, 
            max_len=80, 
        )
    ),
    field.RestField(
        'mixpanel_project',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'enable_kvstore',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'enable_index',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'kvstore_fields',
        required=False,
        encrypted=False,
        default='{"distinct_id":"string","properties":"array"}',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'mixpanel_people',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
