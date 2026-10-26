import {createRequire} from "node:module";
import {resolve,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {readFileSync,writeFileSync} from "node:fs";
const here=dirname(fileURLToPath(import.meta.url)),app=resolve(here,"..");
const modules=process.env.NSEALR_NODE_MODULES;
if(!modules)throw Error("Set NSEALR_NODE_MODULES to an existing pinned pnpm dependency store");
const req=createRequire(resolve(modules,"../package.json"));
const esbuild=req(resolve(modules,"esbuild"));
const root=resolve(app,"../..");
const alias={};
for(const [name,version] of [["curves","2.2.0"],["hashes","2.2.0"],["ciphers","2.1.1"]]) {
 const path=resolve(modules,`.pnpm/@noble+${name}@${version}/node_modules/@noble/${name}`);
 if(JSON.parse(readFileSync(resolve(path,"package.json"),"utf8")).version!==version)throw Error("Wrong pinned dependency");
 alias[`@noble/${name}`]=path;
}
for(const name of ["core","protocol","policy","qr"])
 alias[`@nsealr/${name}`]=resolve(root,`packages/${name}/src/index.ts`);
const result=await esbuild.build({entryPoints:[resolve(here,"client_verify.mjs")],bundle:true,platform:"node",format:"esm",outfile:resolve(app,"evidence/client-verifier.mjs"),alias,metafile:true});
writeFileSync(resolve(app,"evidence/client-verifier-inputs.json"),JSON.stringify(result.metafile,null,2)+"\n");
