"""Validator for the documented JSON Schema subset used by this package.
Not a general JSON Schema implementation. Unsupported schema keywords fail closed.
"""
import re
KEYS = {'$schema','type','additionalProperties','properties','required','const','enum',
        'minLength','pattern','items','minItems','maxItems','uniqueItems'}
def validate(value, schema, path='$'):
    unknown = set(schema) - KEYS
    if unknown: raise ValueError(f'Unsupported schema keywords: {unknown}')
    t = schema.get('type')
    match = {'object': lambda x:isinstance(x,dict), 'array':lambda x:isinstance(x,list),
             'string':lambda x:isinstance(x,str), 'integer':lambda x:type(x) is int,
             'boolean':lambda x:type(x) is bool}
    if t and (t not in match or not match[t](value)): raise ValueError(f'{path}: expected {t}')
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        raise ValueError(f'{path}: incorrect constant')
    if 'enum' in schema and value not in schema['enum']: raise ValueError(f'{path}: invalid enum')
    if isinstance(value,dict):
        props = schema.get('properties',{})
        if set(schema.get('required',[]))-set(value): raise ValueError(f'{path}: missing fields')
        if schema.get('additionalProperties') is False and set(value)-set(props):
            raise ValueError(f'{path}: unknown fields')
        for k,v in value.items():
            if k in props: validate(v, props[k], path+'.'+k)
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',float('inf')):
            raise ValueError(f'{path}: invalid array length')
        if schema.get('uniqueItems') and any(value[i] in value[:i] for i in range(len(value))):
            raise ValueError(f'{path}: duplicate items')
        for i,v in enumerate(value):
            if 'items' in schema: validate(v,schema['items'],f'{path}[{i}]')
    if isinstance(value,str):
        if len(value)<schema.get('minLength',0): raise ValueError(f'{path}: short string')
        if 'pattern' in schema and not re.search(schema['pattern'],value): raise ValueError(f'{path}: pattern mismatch')
