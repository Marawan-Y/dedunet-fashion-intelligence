/**
 * Product media gallery.
 *
 * Replaces the single-image assumption. The API ships an ordered `media` array; this
 * renders it in that order and never re-sorts, because `sort_order` is assigned
 * deterministically at build time and reshuffling it here would make the gallery differ
 * between platforms.
 *
 * Three states that are genuinely different and must not be collapsed:
 *   - media present   -> render the strip
 *   - media absent    -> render nothing at all (not a broken image, not a spinner)
 *   - image failed    -> per-image placeholder, the rest of the gallery still works
 *
 * Concept artwork is labelled as such. These SVGs are prototype media, not product
 * photography, and a gallery that looks like a catalogue shoot invites exactly that
 * misreading.
 */

import React, { useCallback, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { Image } from "expo-image";

import type { Product, ProductMedia } from "../api/types";
import { BRAND } from "../brand";
import { Body, styles } from "../ui";

const ROLE_LABEL: Record<string, string> = {
  front: "Front",
  back: "Back",
  detail: "Detail",
  lifestyle: "In context",
  campaign: "Campaign",
  collection: "Collection",
};

export function Gallery({ product, apiBase }: { product: Product; apiBase: string }) {
  const [failed, setFailed] = useState<Record<string, boolean>>({});

  const onError = useCallback((assetId: string) => {
    setFailed((previous) => ({ ...previous, [assetId]: true }));
  }, []);

  const media = product.media ?? [];

  // No media is a normal state for the legacy fixture catalogue. Rendering an empty strip
  // or a broken image would present a defect where there is none.
  if (media.length === 0) return null;

  const isConcept = media.some((m) => m.status === "PROTOTYPE_CONCEPT");

  return (
    <View testID="product-gallery" style={{ gap: 8 }}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: 10 }}
        accessibilityLabel={`${product.name} images, ${media.length} available`}
      >
        {media.map((item) => (
          <GalleryImage
            key={item.asset_id}
            item={item}
            productName={product.name}
            uri={`${apiBase}${item.url}`}
            failed={failed[item.asset_id] === true}
            onError={() => onError(item.asset_id)}
          />
        ))}
      </ScrollView>

      {isConcept ? (
        <Body muted>Concept artwork — not product photography.</Body>
      ) : null}
    </View>
  );
}

function GalleryImage({
  item,
  productName,
  uri,
  failed,
  onError,
}: {
  item: ProductMedia;
  productName: string;
  uri: string;
  failed: boolean;
  onError: () => void;
}) {
  const role = ROLE_LABEL[item.role] ?? item.role;

  // Side A supplies alt text per asset. It is preferred over anything generated here,
  // because it was written by the people who made the image.
  const label = item.alt_text?.trim()
    ? item.alt_text
    : `${productName} — ${role.toLowerCase()} view`;

  if (failed) {
    return (
      <View
        testID={`gallery-failed-${item.asset_id}`}
        accessibilityRole="image"
        accessibilityLabel={`${label} (image unavailable)`}
        style={{
          width: 200,
          height: 240,
          borderRadius: 8,
          borderWidth: 1,
          borderColor: BRAND.palette.border,
          backgroundColor: BRAND.palette.surface,
          alignItems: "center",
          justifyContent: "center",
          padding: 12,
        }}
      >
        <Text style={[styles.body, styles.bodyMuted, { textAlign: "center" }]}>
          {role} image unavailable
        </Text>
      </View>
    );
  }

  return (
    <View testID={`gallery-item-${item.asset_id}`} style={{ gap: 4 }}>
      <Image
        testID={`gallery-image-${item.asset_id}`}
        source={{ uri }}
        onError={onError}
        accessible
        accessibilityLabel={label}
        contentFit="contain"
        style={{
          width: 200,
          height: 240,
          borderRadius: 8,
          borderWidth: 1,
          borderColor: BRAND.palette.border,
          backgroundColor: BRAND.palette.surface,
        }}
      />
      <Text style={[styles.body, styles.bodyMuted]}>{role}</Text>
    </View>
  );
}
