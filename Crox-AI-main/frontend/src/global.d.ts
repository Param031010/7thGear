interface Window {
  workflowos?: {
    backendUrl: string;
  };
}

declare module "*.png" {
  const src: string;
  export default src;
}
