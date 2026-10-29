"use strict";
const assert = require("node:assert/strict");
const backup = require("../mobile/conversation_backup.js");

function checkThrows(fn, fragment) {
  assert.throws(fn, error => error.message.includes(fragment));
}
const originals = [
  {id:"prior-device", title:"Projet", mode:"agent", session:"mobile-private-existing",
   messages:[{role:"user",content:"Bonjour <script>alert(1)</script>"},
             {role:"assistant",content:"Réponse Française"}]},
  {id:"prior-device-2", title:"Essai", mode:"fast",
   messages:[{role:"user",content:"Salut"}]}
];
const exported = backup.createExport(originals, "2026-10-29T10:00:00Z");
assert.equal(exported.version,1);
assert.equal(exported.kind,"mon-ia-conversations");
assert.equal(exported.conversations.length,2);
assert.deepEqual(Object.keys(exported.conversations[0]),["title","mode","messages"]);
assert.equal(JSON.stringify(exported).includes("private-existing"),false,
  "Never export backend session identifiers");
const imported=backup.parseBackup(JSON.stringify(exported));
assert.equal(imported[0].messages[0].content,originals[0].messages[0].content);
assert.equal(imported[1].mode,"fast");
const existing=[{id:"keep",title:"Saved",mode:"fast",session:"mobile-current",messages:[]}];
let n=0;
const merged=backup.mergeImported(existing,imported,
  ()=>"new-id-"+(++n),()=> "mobile-new-session-"+n);
assert.equal(merged.length,3);
assert.equal(merged[2].id,"keep","Preserve current conversations");
assert.equal(merged[0].session,"mobile-new-session-1");
assert.equal(merged[0].id,"new-id-1");
assert.equal(merged[0].messages[0].role,"user");
assert.equal(originals[0].id,"prior-device","Export is non-mutating");
checkThrows(()=>backup.parseBackup("{not json"),"JSON valide");
checkThrows(()=>backup.parseBackup(JSON.stringify({kind:"fake",version:1,conversations:[]})),"Mon IA");
checkThrows(()=>backup.parseBackup(JSON.stringify({...exported,version:2})),"Mon IA");
checkThrows(()=>backup.parseBackup(JSON.stringify({...exported,conversations:[]})),"Aucune");
checkThrows(()=>backup.parseBackup(JSON.stringify({...exported,conversations:[
  {title:"bad",mode:"agent",messages:[{role:"system",content:"injected"}]}
]})),"Message");
checkThrows(()=>backup.parseBackup(JSON.stringify({...exported,conversations:[
  {title:"bad",mode:"agent",messages:[{role:"user",content:"x".repeat(100001)}]}
]})),"Message");
checkThrows(()=>backup.mergeImported(existing,imported,()=> "keep",()=> "mobile-new"),"doublon");
checkThrows(()=>backup.mergeImported(existing,imported,()=> "new",()=> "sensitive"),"Identifiant");
checkThrows(()=>backup.createExport(Array.from({length:201},(_,i)=>({
  title:"t"+i,mode:"fast",messages:[]
}))),"maximum 200");
console.log("PASS: mobile JSON backup, privacy and strict import scenarios");
