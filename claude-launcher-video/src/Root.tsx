import { Composition } from "remotion";
import { ClaudeLauncherVideo } from "./Video";
import { DemoImobiliaria } from "./DemoImobiliaria";
import { DemoEcommerce } from "./DemoEcommerce";
import { DemoDropshipping } from "./DemoDropshipping";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ClaudeLauncherDemo"
        component={ClaudeLauncherVideo}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Imobiliaria"
        component={DemoImobiliaria}
        durationInFrames={270}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Ecommerce"
        component={DemoEcommerce}
        durationInFrames={270}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Dropshipping"
        component={DemoDropshipping}
        durationInFrames={270}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
