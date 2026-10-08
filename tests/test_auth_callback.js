'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('frontend/assets/practice.js', 'utf8');

function environment(hash, reject = false) {
  const values = new Map([['dhanvest-paper-retry', '{"symbol":"OLD"}']]);
  const nodes = new Map(), requests = [];
  function node() { return {value:'buy', dataset:{}, options:[], textContent:'',
    addEventListener(){},setAttribute(){},focus(){},reportValidity(){return true;},
    replaceChildren(){this.options=[];},append(child){this.options.push(child);}}; }
  const location = {hash, pathname:'/v2/practice', search:''};
  const sandbox = {
    URLSearchParams, AbortController, console, location,
    history:{replaceState(_,__,url){location.hash='';location.pathname=url;}},
    sessionStorage:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},
    document:{getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},createElement:node},
    setInterval(){},setTimeout(){},clearTimeout(){},
    fetch:async(path,options)=>{
      requests.push({path,options});
      if(reject && path==='/api/paper/portfolio')return {ok:false,status:401,json:async()=>({detail:'Please sign in again.'})};
      return {ok:true,json:async()=>path==='/api/market'?{quotes:[],session:{isOpen:false,sessionDate:'2026-10-08'},retrieved_at:'2026-10-08T00:00:00Z'}:{account:{cash:1000000},positions:[],trades:[],equity:1000000,total_pnl:0}};
    }
  };
  vm.runInNewContext(source,sandbox);
  return {values,nodes,requests,location};
}

test('confirmation callback consumes token, removes URL secrets and clears stale trade retry',async()=>{
  const state=environment('#access_token=synthetic-qa-token&refresh_token=private-fixture&type=signup');
  await new Promise(setImmediate);
  assert.equal(state.location.hash,'');
  assert.equal(state.values.get('dhanvest-paper-session'),'synthetic-qa-token');
  assert.equal(state.values.has('dhanvest-paper-retry'),false);
  assert.equal(state.nodes.get('workspace').hidden,false);
  assert.match(state.nodes.get('status').textContent,/Email confirmed/);
  assert.equal(state.requests[0].options.headers.Authorization,'Bearer synthetic-qa-token');
  assert.equal([...state.values.values()].some(v=>v.includes('private-fixture')),false);
});
test('expired confirmation gives recovery guidance and performs no account request',()=>{
  const state=environment('#error=access_denied&error_code=otp_expired');
  assert.equal(state.location.hash,'');
  assert.equal(state.requests.length,0);
  assert.match(state.nodes.get('status').textContent,/expired or already used/);
});
test('rejected callback token never displays confirmation success',async()=>{
  const state=environment('#access_token=invalid-fixture&type=signup',true);
  await new Promise(setImmediate);
  assert.equal(state.values.has('dhanvest-paper-session'),false);
  assert.equal(state.nodes.get('workspace').hidden,true);
  assert.doesNotMatch(state.nodes.get('status').textContent,/Email confirmed/);
});
