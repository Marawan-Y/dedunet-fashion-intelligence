from __future__ import annotations

from .schemas import Product, StylistRecommendation, StylistRequest


def recommend_products(
    request: StylistRequest, products: list[Product]
) -> StylistRecommendation:
    """Deterministic PoC recommender.

    It demonstrates the data contract without sending personal data to a third-party
    model. Production can replace this scorer with embeddings, ranking, and an LLM
    explanation after consent, evaluation, and privacy controls are in place.

    Money rule (SB-AR-B3-003): budget and totals are compared and accumulated as
    integer minor units. Scoring weights are ordinary floats and are not money.
    """

    preferred_colors = {item.lower() for item in request.preferred_colors}
    preferred_categories = {item.lower() for item in request.preferred_categories}
    query_terms = set(
        (request.occasion + " " + request.style_notes).lower().replace(",", " ").split()
    )

    scored: list[tuple[float, Product]] = []
    for product in products:
        if product.currency != request.currency:
            continue
        if product.price_minor_units > request.budget_minor_units:
            continue
        score = 0.0
        if product.category in preferred_categories:
            score += 4.0
        colors = {variant.color.lower() for variant in product.variants}
        score += 2.0 * len(preferred_colors.intersection(colors))
        score += 1.5 * len(query_terms.intersection(set(product.style_tags)))
        score += 0.25 * sum(variant.stock for variant in product.variants)
        scored.append((score, product))

    scored.sort(key=lambda pair: (-pair[0], pair[1].price_minor_units))
    selected: list[Product] = []
    running_total_minor_units = 0
    for _, product in scored:
        if running_total_minor_units + product.price_minor_units <= request.budget_minor_units:
            selected.append(product)
            running_total_minor_units += product.price_minor_units
        if len(selected) == 3:
            break

    if not selected:
        return StylistRecommendation(
            rationale="No active product matched the stated budget and preferences.",
            product_ids=[],
            total_minor_units=0,
            currency=request.currency,
        )

    names = ", ".join(item.name for item in selected)
    rationale = (
        f"Selected {names} because the products fit the requested budget, "
        "available stock, preferred categories, colors, and style keywords."
    )
    return StylistRecommendation(
        rationale=rationale,
        product_ids=[item.id for item in selected],
        total_minor_units=running_total_minor_units,
        currency=request.currency,
    )
