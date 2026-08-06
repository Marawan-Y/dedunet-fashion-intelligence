# packages/brand — GENERATED

Normalized runtime brand package. **Do not edit by hand.**

Regenerate with:

```bash
python scripts/brand/build_brand_package.py
```

Source of truth is the immutable Side A delivery at
`handoffs/incoming/side-a/DEDUNET_Platform_Integration_v1/`, which this build reads
and never modifies. Applications read THIS directory, never the handoff.

Money here is integer minor units. Product and variant identity is the Side A
`external_product_id` / `external_variant_id`, never array position or insertion order.
