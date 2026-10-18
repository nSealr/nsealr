#!/usr/bin/env node
// Validate command/flag names against the actual Commander tree without actions.
import assert from "node:assert/strict";
import {readFileSync,readdirSync,existsSync} from "node:fs";
import {join} from "node:path";
import {pathToFileURL} from "node:url";
import * as ts from "typescript";
import {buildCli} from "../../apps/bridge/cli/src/index.ts";
import {root} from "./package_set.mjs";
import {checkFeatureClaims,checkCurrentOwnerLinks} from "./check_product_boundaries.mjs";
const cli=buildCli();
const source=ts.createSourceFile("cli.ts",readFileSync(join(root,"apps/bridge/cli/src/index.ts"),"utf8"),ts.ScriptTarget.Latest,true);
const objects=new Map();
function walk(node,fn){fn(node);ts.forEachChild(node,child=>walk(child,fn));}
walk(source,node=>{if(ts.isVariableDeclaration(node)&&ts.isIdentifier(node.name)&&node.initializer&&ts.isObjectLiteralExpression(node.initializer))objects.set(node.name.text,node.initializer.properties.map(p=>p.name?.text).filter(Boolean));});
const actions=new Map();
walk(source,node=>{
 if(!ts.isCallExpression(node)||!ts.isPropertyAccessExpression(node.expression)||node.expression.name.text!=="action")return;
 const fn=node.arguments[0];if(!fn||!ts.isArrowFunction(fn)||!fn.parameters[0]||!ts.isIdentifier(fn.parameters[0].name))return;
 let chain=node.expression.expression,command;
 while(ts.isCallExpression(chain)&&ts.isPropertyAccessExpression(chain.expression)){
  if(chain.expression.name.text==="command"&&chain.arguments[0]&&ts.isStringLiteral(chain.arguments[0]))command=chain.arguments[0].text;
  chain=chain.expression.expression;
 }
 if(!command)return;
 const parameter=fn.parameters[0].name.text,values=new Set();
 walk(fn.body,n=>{
  if(ts.isBinaryExpression(n)&&ts.isIdentifier(n.left)&&n.left.text===parameter&&ts.isStringLiteral(n.right)&&[ts.SyntaxKind.EqualsEqualsEqualsToken,ts.SyntaxKind.ExclamationEqualsEqualsToken].includes(n.operatorToken.kind))values.add(n.right.text);
  if(ts.isElementAccessExpression(n)&&ts.isIdentifier(n.expression)&&ts.isIdentifier(n.argumentExpression)&&n.argumentExpression.text===parameter)for(const value of objects.get(n.expression.text)??[])values.add(value);
 });
 if(values.size)actions.set(command,values);
});
export function checkCliExcerpt(text){
 const tokens=(text.replace(/\\\s*\n/gu," ").match(/"[^"\n]*"|'[^'\n]*'|[^\s]+/gu)??[]).map(x=>x.replace(/^['"]|['"]$/gu,""));
 const begin=tokens.indexOf("nsealr");assert(begin>=0,"CLI excerpt must contain nsealr");
 let command=cli;const positionals=[];
 for(let i=begin+1;i<tokens.length;i++){
  const token=tokens[i];if(token==="...")continue;
  if(token.startsWith("--")){
   const option=command.options.find(o=>o.long===token.split("=")[0]);assert(option,`unknown flag ${token} for ${command.name()}`);
   if((option.required||option.optional)&&!token.includes("="))i++;
   continue;
  }
  if(token.startsWith("-")){assert(command.options.some(o=>o.short===token),`unknown flag ${token}`);continue;}
  const child=command.commands.find(c=>c.name()===token);
  if(child){command=child;continue;}
  assert(!command.commands.length,`unknown command ${token} under ${command.name()}`);
  positionals.push(token);
 }
 const domain=actions.get(command.name());
 if(domain&&positionals[0]&&!/[<$]/u.test(positionals[0]))assert(domain.has(positionals[0]),`unsupported ${command.name()} action ${positionals[0]}`);
 return command;
}
export function checkGuide(path,text){
 if(path.endsWith(".test.ts"))return;
 checkCurrentOwnerLinks(text);checkFeatureClaims(text);
 for(const match of text.matchAll(/`([^`]+)`/gu))if(/^(?:pnpm\s+)?nsealr\s/u.test(match[1].trim()))checkCliExcerpt(match[1].trim());
 for(const line of text.replace(/\\\s*\n/gu," ").split("\n"))if(/^\s*(?:pnpm\s+)?nsealr\s/u.test(line))checkCliExcerpt(line.trim());
}
export function allCurrentCommandExamples(){
 const examples=[];
 function visit(command,prefix){
  const path=[...prefix,command.name()];
  if(!command.commands.length){
   const positional=actions.get(command.name())?.values().next().value;
   examples.push([...path,...(positional?[positional]:[])].join(" "));
   for(const option of command.options)if(option.long)examples.push([...path,...(positional?[positional]:[]),option.long,...(option.required||option.optional?["example"]:[])].join(" "));
  }
  for(const child of command.commands)visit(child,path);
 }
 visit(cli,[]);return examples;
}
function markdown(dir){return readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?markdown(join(dir,e.name)):e.isFile()&&e.name.endsWith(".md")?[join(dir,e.name)]:[]);}
export function main(){
 const paths=["README.md","AGENTS.md",...markdown(join(root,"docs/bridge")),...markdown(join(root,"docs/product")),...markdown(join(root,"apps/pi/docs"))];
 for(const name of readdirSync(join(root,"packages")))if(existsSync(join(root,"packages",name,"README.md")))paths.push(join(root,"packages",name,"README.md"));
 for(const path of paths)checkGuide(path,readFileSync(path.startsWith("/")?path:join(root,path),"utf8"));
 console.log(`current guide command/flag, public owner and feature claims checked in ${paths.length} files`);
}
if(import.meta.url===pathToFileURL(process.argv[1]).href)main();
