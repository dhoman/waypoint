"""Closed predicate and output language; never execute model-provided code."""

import re
from decimal import Decimal


async def holds(predicate, observation, inputs, browser):
    p = predicate
    refs = [p.input]
    if p.target:
        refs.extend([p.target.name_input, p.target.row_input])
    if any(ref and ref not in inputs for ref in refs):
        raise ValueError("unknown predicate input")
    if p.op == "heading":
        return p.value in observation.headings
    if p.op == "heading_input":
        return str(inputs[p.input]) in observation.headings
    if p.op == "title":
        return p.value == observation.title
    if p.op == "text_present":
        return p.value in observation.text
    if p.op == "field_equals_input":
        return observation.fields.get(p.field) == str(inputs[p.input])
    if p.op == "field_equals":
        return observation.fields.get(p.field) == p.value
    if p.op == "no_dialog":
        return not observation.dialog
    if p.op == "table_present":
        return sum(t["caption"] == p.value for t in observation.tables) == 1
    if p.op in {"target_present", "target_text_input"}:
        try:
            resolved = await browser.resolve(p.target, inputs)
            return (
                resolved["visible"]
                if p.op == "target_present"
                else await browser.read(p.target, inputs) == str(inputs[p.input])
            )
        except ValueError:
            return False
    raise ValueError("unsupported predicate")


async def check(predicates, obs, inputs, browser):
    return [await holds(p, obs, inputs, browser) for p in predicates]


async def recognize(screens, obs, inputs, browser):
    checks = {
        key: await check(screen.recognition, obs, inputs, browser)
        for key, screen in screens.items()
    }
    matches = [key for key, passed in checks.items() if all(passed)]
    # Identity remains mandatory beneath an overlay if recognizable landmarks exist.
    for key in matches:
        if not all(await check(screens[key].identity, obs, inputs, browser)):
            raise ValueError("identity binding failed for " + key)
    if obs.dialog:
        return "unknown", None, {"blocking_dialog": True, **checks}
    if obs.loading:
        return "transient", None, checks
    if len(matches) > 1:
        return "ambiguous", None, checks
    return ("recognized", matches[0], checks) if matches else ("unknown", None, checks)


def convert(value, kind):
    value = str(value).strip()
    if kind == "string":
        return value
    if kind == "boolean":
        if value.lower() not in {"true", "false", "yes", "no"}:
            raise ValueError("output is not a boolean")
        return value.lower() in {"true", "yes"}
    # Explicit decimal-dot/thousands-comma grammar; ambiguous locales fail.
    match = re.fullmatch(
        r"[^\d+\-]*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)[^\d]*", value
    )
    if not match:
        raise ValueError("output is not an unambiguous number")
    return float(Decimal(match[1].replace(",", "")))


async def extract(specs, observation, inputs, browser):
    output = {}
    for spec in specs:
        if spec.source == "input":
            value = inputs[spec.field]
        elif spec.source == "field":
            if spec.field not in observation.fields:
                raise ValueError("output field missing: " + spec.field)
            value = observation.fields[spec.field]
        elif spec.source == "sum":
            collection, column = spec.field.split(".", 1)
            output[spec.name] = float(
                sum(Decimal(str(row[column])) for row in output[collection])
            )
            continue
        elif spec.source in {"text", "attribute"}:
            value = await browser.read(spec.target, inputs, spec.attribute)
        elif spec.source == "table":
            tables = [t for t in observation.tables if t["caption"] == spec.field]
            if len(tables) != 1:
                raise ValueError("ambiguous or missing output table")
            table = tables[0]
            rows = []
            if len(set(table["headers"])) != len(table["headers"]):
                raise ValueError("ambiguous column headers")
            for row in table["rows"][: spec.limit]:
                rows.append(
                    {
                        c.name: convert(
                            row[table["headers"].index(c.field)], c.value_type
                        )
                        for c in spec.columns
                    }
                )
            output[spec.name] = rows
            continue
        elif spec.source == "list":
            rows = await browser.read_rows(
                spec.target, spec.columns, inputs, spec.limit
            )
            output[spec.name] = [
                {
                    col.name: convert(row[col.name], col.value_type)
                    for col in spec.columns
                }
                for row in rows
            ]
            continue
        else:
            raise ValueError("unsupported extraction")
        output[spec.name] = convert(value, spec.value_type)
    return output
