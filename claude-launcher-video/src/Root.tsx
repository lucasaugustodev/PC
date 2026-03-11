import { Composition } from "remotion";
import { ClaudeLauncherVideo } from "./Video";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ClaudeLauncherDemo"
      component={ClaudeLauncherVideo}
      durationInFrames={450}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
