import { LAYERS, LAYER_LABEL, type LayerId, type LayerView } from "./view";

export function LayerPanel({
  layers,
  onChange,
}: {
  layers: Record<LayerId, LayerView>;
  onChange: (layer: LayerId, next: LayerView) => void;
}) {
  return (
    <fieldset className="layer-panel">
      <legend>Layers</legend>
      {LAYERS.map((id) => {
        const layer = layers[id];
        const label = LAYER_LABEL[id];
        return (
          <div key={id} className="layer-panel__row" data-layer={id}>
            <label className="layer-panel__toggle">
              <input
                type="checkbox"
                aria-label={`Show ${label.toLowerCase()}`}
                checked={layer.visible}
                onChange={(e) => onChange(id, { ...layer, visible: e.target.checked })}
              />
              <span className="layer-panel__swatch" aria-hidden="true" />
              {label}
            </label>
            <input
              type="range"
              aria-label={`${label} opacity`}
              min={0}
              max={100}
              step={5}
              value={Math.round(layer.opacity * 100)}
              disabled={!layer.visible}
              onChange={(e) => onChange(id, { ...layer, opacity: Number(e.target.value) / 100 })}
            />
          </div>
        );
      })}
    </fieldset>
  );
}
