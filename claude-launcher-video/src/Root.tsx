import { Composition } from "remotion";
import { ClaudeLauncherVideo } from "./Video";
import { DemoImobiliaria } from "./DemoImobiliaria";
import { DemoEcommerce } from "./DemoEcommerce";
import { DemoDropshipping } from "./DemoDropshipping";
import { EcommerceH, EcommerceV } from "./DemoEcommerceV3";

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
      <Composition
        id="EcommerceV3"
        component={EcommerceH}
        durationInFrames={285}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="EcommerceReels"
        component={EcommerceV}
        durationInFrames={285}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
