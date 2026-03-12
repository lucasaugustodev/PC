import json, os

base = os.path.dirname(os.path.abspath(__file__))
svg_out = os.path.join(os.path.dirname(base), "..", "public", "svg")
os.makedirs(svg_out, exist_ok=True)

specs = {}

specs["react-atom.json"] = {
    "canvas": {"width": 200, "height": 200, "viewBox": "0 0 200 200", "units": "px", "background": "none"},
    "elements": [
        {"type": "ellipse", "cx": 100, "cy": 100, "rx": 80, "ry": 28, "style": {"fill": "none", "stroke": "#61dafb", "strokeWidth": 3}},
        {"type": "ellipse", "cx": 100, "cy": 100, "rx": 80, "ry": 28, "style": {"fill": "none", "stroke": "#61dafb", "strokeWidth": 3}, "transform": [{"rotate": [60, 100, 100]}]},
        {"type": "ellipse", "cx": 100, "cy": 100, "rx": 80, "ry": 28, "style": {"fill": "none", "stroke": "#61dafb", "strokeWidth": 3}, "transform": [{"rotate": [120, 100, 100]}]},
        {"type": "circle", "cx": 100, "cy": 100, "r": 10, "style": {"fill": "#61dafb"}}
    ],
    "metadata": {"title": "React atom logo"}
}

specs["film-icon.json"] = {
    "canvas": {"width": 120, "height": 120, "viewBox": "0 0 120 120", "units": "px", "background": "none"},
    "elements": [
        {"type": "rect", "x": 15, "y": 10, "width": 90, "height": 100, "rx": 8, "ry": 8, "style": {"fill": "none", "stroke": "#cba6f7", "strokeWidth": 3}},
        {"type": "rect", "x": 15, "y": 10, "width": 18, "height": 100, "style": {"fill": "none", "stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "rect", "x": 87, "y": 10, "width": 18, "height": 100, "style": {"fill": "none", "stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "line", "x1": 15, "y1": 35, "x2": 33, "y2": 35, "style": {"stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "line", "x1": 15, "y1": 60, "x2": 33, "y2": 60, "style": {"stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "line", "x1": 15, "y1": 85, "x2": 33, "y2": 85, "style": {"stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "line", "x1": 87, "y1": 35, "x2": 105, "y2": 35, "style": {"stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "line", "x1": 87, "y1": 60, "x2": 105, "y2": 60, "style": {"stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "line", "x1": 87, "y1": 85, "x2": 105, "y2": 85, "style": {"stroke": "#cba6f7", "strokeWidth": 2}},
        {"type": "path", "d": "M50 45 L50 75 L72 60 Z", "style": {"fill": "#cba6f7", "stroke": "none"}}
    ],
    "metadata": {"title": "Film reel icon"}
}

specs["code-bracket.json"] = {
    "canvas": {"width": 120, "height": 120, "viewBox": "0 0 120 120", "units": "px", "background": "none"},
    "elements": [
        {"type": "path", "d": "M45 25 L15 60 L45 95", "style": {"fill": "none", "stroke": "#89b4fa", "strokeWidth": 4, "strokeLinecap": "round", "strokeLinejoin": "round"}},
        {"type": "path", "d": "M75 25 L105 60 L75 95", "style": {"fill": "none", "stroke": "#89b4fa", "strokeWidth": 4, "strokeLinecap": "round", "strokeLinejoin": "round"}},
        {"type": "line", "x1": 68, "y1": 20, "x2": 52, "y2": 100, "style": {"stroke": "#a6e3a1", "strokeWidth": 3, "strokeLinecap": "round"}}
    ],
    "metadata": {"title": "Code brackets icon"}
}

specs["pipeline.json"] = {
    "canvas": {"width": 1400, "height": 200, "viewBox": "0 0 1400 200", "units": "px", "background": "none"},
    "defs": {
        "markers": [{"id": "arrow", "markerWidth": 12, "markerHeight": 12, "refX": 10, "refY": 6, "orient": "auto", "pathD": "M0 0 L12 6 L0 12 Z", "style": {"fill": "#89b4fa"}}],
        "gradients": [{"type": "linear", "id": "boxGrad", "x1": 0, "y1": 0, "x2": 0, "y2": 1, "stops": [{"offset": 0, "color": "#313244"}, {"offset": 1, "color": "#1e1e2e"}]}]
    },
    "elements": [
        {"type": "rect", "x": 20, "y": 40, "width": 240, "height": 120, "rx": 16, "ry": 16, "style": {"fill": "url(#boxGrad)", "stroke": "#89b4fa", "strokeWidth": 2}},
        {"type": "text", "x": 140, "y": 90, "text": "React JSX", "anchor": "middle", "baseline": "middle", "style": {"fill": "#89b4fa", "fontSize": 26, "fontWeight": 700, "fontFamily": "monospace"}},
        {"type": "text", "x": 140, "y": 120, "text": "Components", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6adc8", "fontSize": 16, "fontFamily": "monospace"}},
        {"type": "line", "x1": 260, "y1": 100, "x2": 360, "y2": 100, "style": {"stroke": "#89b4fa", "strokeWidth": 3, "markerEnd": "url(#arrow)"}},
        {"type": "rect", "x": 370, "y": 40, "width": 240, "height": 120, "rx": 16, "ry": 16, "style": {"fill": "url(#boxGrad)", "stroke": "#a6e3a1", "strokeWidth": 2}},
        {"type": "text", "x": 490, "y": 90, "text": "Bundler", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6e3a1", "fontSize": 26, "fontWeight": 700, "fontFamily": "monospace"}},
        {"type": "text", "x": 490, "y": 120, "text": "Webpack", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6adc8", "fontSize": 16, "fontFamily": "monospace"}},
        {"type": "line", "x1": 610, "y1": 100, "x2": 710, "y2": 100, "style": {"stroke": "#a6e3a1", "strokeWidth": 3, "markerEnd": "url(#arrow)"}},
        {"type": "rect", "x": 720, "y": 40, "width": 240, "height": 120, "rx": 16, "ry": 16, "style": {"fill": "url(#boxGrad)", "stroke": "#f9e2af", "strokeWidth": 2}},
        {"type": "text", "x": 840, "y": 90, "text": "Renderer", "anchor": "middle", "baseline": "middle", "style": {"fill": "#f9e2af", "fontSize": 26, "fontWeight": 700, "fontFamily": "monospace"}},
        {"type": "text", "x": 840, "y": 120, "text": "Headless Chrome", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6adc8", "fontSize": 16, "fontFamily": "monospace"}},
        {"type": "line", "x1": 960, "y1": 100, "x2": 1060, "y2": 100, "style": {"stroke": "#f9e2af", "strokeWidth": 3, "markerEnd": "url(#arrow)"}},
        {"type": "rect", "x": 1070, "y": 40, "width": 240, "height": 120, "rx": 16, "ry": 16, "style": {"fill": "url(#boxGrad)", "stroke": "#f38ba8", "strokeWidth": 2}},
        {"type": "text", "x": 1190, "y": 90, "text": "MP4", "anchor": "middle", "baseline": "middle", "style": {"fill": "#f38ba8", "fontSize": 30, "fontWeight": 700, "fontFamily": "monospace"}},
        {"type": "text", "x": 1190, "y": 120, "text": "H.264 Video", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6adc8", "fontSize": 16, "fontFamily": "monospace"}}
    ],
    "metadata": {"title": "Remotion render pipeline"}
}

specs["concepts.json"] = {
    "canvas": {"width": 1200, "height": 300, "viewBox": "0 0 1200 300", "units": "px", "background": "none"},
    "defs": {
        "gradients": [{"type": "linear", "id": "card1", "x1": 0, "y1": 0, "x2": 0, "y2": 1, "stops": [{"offset": 0, "color": "#313244"}, {"offset": 1, "color": "#1e1e2e"}]}]
    },
    "elements": [
        {"type": "rect", "x": 20, "y": 20, "width": 350, "height": 260, "rx": 20, "ry": 20, "style": {"fill": "url(#card1)", "stroke": "#89b4fa", "strokeWidth": 2}},
        {"type": "rect", "x": 20, "y": 20, "width": 350, "height": 6, "rx": 3, "ry": 3, "style": {"fill": "#89b4fa"}},
        {"type": "text", "x": 195, "y": 80, "text": "Composition", "anchor": "middle", "baseline": "middle", "style": {"fill": "#89b4fa", "fontSize": 28, "fontWeight": 700, "fontFamily": "monospace"}},
        {"type": "text", "x": 195, "y": 130, "text": "fps, width, height", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6adc8", "fontSize": 17, "fontFamily": "monospace"}},
        {"type": "rect", "x": 50, "y": 175, "width": 290, "height": 50, "rx": 8, "ry": 8, "style": {"fill": "#11111b", "stroke": "#45475a", "strokeWidth": 1}},
        {"type": "text", "x": 195, "y": 205, "text": "fps={30} w={1920}", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6e3a1", "fontSize": 15, "fontFamily": "monospace"}},
        {"type": "rect", "x": 420, "y": 20, "width": 350, "height": 260, "rx": 20, "ry": 20, "style": {"fill": "url(#card1)", "stroke": "#a6e3a1", "strokeWidth": 2}},
        {"type": "rect", "x": 420, "y": 20, "width": 350, "height": 6, "rx": 3, "ry": 3, "style": {"fill": "#a6e3a1"}},
        {"type": "text", "x": 595, "y": 80, "text": "Sequence", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6e3a1", "fontSize": 28, "fontWeight": 700, "fontFamily": "monospace"}},
        {"type": "text", "x": 595, "y": 130, "text": "Timeline scenes", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6adc8", "fontSize": 17, "fontFamily": "monospace"}},
        {"type": "rect", "x": 450, "y": 185, "width": 90, "height": 25, "rx": 4, "ry": 4, "style": {"fill": "#89b4fa", "opacity": 0.7}},
        {"type": "rect", "x": 550, "y": 185, "width": 90, "height": 25, "rx": 4, "ry": 4, "style": {"fill": "#a6e3a1", "opacity": 0.7}},
        {"type": "rect", "x": 650, "y": 185, "width": 90, "height": 25, "rx": 4, "ry": 4, "style": {"fill": "#f9e2af", "opacity": 0.7}},
        {"type": "rect", "x": 820, "y": 20, "width": 350, "height": 260, "rx": 20, "ry": 20, "style": {"fill": "url(#card1)", "stroke": "#f9e2af", "strokeWidth": 2}},
        {"type": "rect", "x": 820, "y": 20, "width": 350, "height": 6, "rx": 3, "ry": 3, "style": {"fill": "#f9e2af"}},
        {"type": "text", "x": 995, "y": 80, "text": "useCurrentFrame", "anchor": "middle", "baseline": "middle", "style": {"fill": "#f9e2af", "fontSize": 26, "fontWeight": 700, "fontFamily": "monospace"}},
        {"type": "text", "x": 995, "y": 130, "text": "Frame animation", "anchor": "middle", "baseline": "middle", "style": {"fill": "#a6adc8", "fontSize": 17, "fontFamily": "monospace"}},
        {"type": "rect", "x": 850, "y": 175, "width": 290, "height": 50, "rx": 8, "ry": 8, "style": {"fill": "#11111b", "stroke": "#45475a", "strokeWidth": 1}},
        {"type": "text", "x": 995, "y": 205, "text": "interpolate(f,...)", "anchor": "middle", "baseline": "middle", "style": {"fill": "#f9e2af", "fontSize": 15, "fontFamily": "monospace"}}
    ],
    "metadata": {"title": "Remotion core concepts"}
}

for name, spec in specs.items():
    path = os.path.join(base, name)
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"OK {name}")

print("All specs created")
