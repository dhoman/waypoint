() => {
  const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const text = e => (e?.innerText || '').trim();
  const safe = e => !['password','hidden','file'].includes(e.type);
  const name = e => e.getAttribute('aria-label') || (e.labels?.length ? text(e.labels[0]) : '') || text(e) || e.getAttribute('title') || e.getAttribute('placeholder') || '';
  const role = e => e.getAttribute('role') || ({A:'link',BUTTON:'button',SELECT:'combobox',TEXTAREA:'textbox',INPUT:e.type==='checkbox'?'checkbox':e.type==='submit'?'button':'textbox'})[e.tagName] || '';
  function selector(e) {
    if(e.id && !/\d{6,}/.test(e.id)) return '#'+CSS.escape(e.id);
    let part=e.tagName.toLowerCase();
    if(e.getAttribute('name')) return part+'[name='+JSON.stringify(e.getAttribute('name'))+']';
    const classes=[...e.classList].filter(c=>!/[0-9]{5}|:/.test(c)).slice(0,2);
    if(classes.length)part+='.'+classes.map(CSS.escape).join('.');
    return part;
  }
  function target(e) {
    const label=e.getAttribute('aria-label')||(e.labels?.length?text(e.labels[0]):'');
    if(label) return {by:'label',name:label,role:role(e)};
    if(e.title) return {by:'title',name:e.title,role:role(e)};
    if(role(e)&&name(e)) return {by:'role',role:role(e),name:name(e)};
    if(e.placeholder) return {by:'placeholder',name:e.placeholder,role:role(e)};
    return {by:'css',name:selector(e),role:role(e)};
  }
  const fields={};
  for(const e of document.querySelectorAll('dt')) if(visible(e)) {const key=text(e);fields[key]=key in fields?'[ambiguous]':text(e.nextElementSibling)}
  for(const e of document.querySelectorAll('input,select,textarea')) if(visible(e)&&safe(e)&&name(e)) fields['input:'+name(e)]=e.value;
  const controls=[...document.querySelectorAll('a,button,input,select,textarea,[role=button],[role=tab],[role=menuitem]')].filter(e=>visible(e)&&safe(e)).slice(0,180).map(e=>({target:target(e),name:name(e),role:role(e),row:e.closest('tr')?text(e.closest('tr')):null,options:e.tagName==='SELECT'?[...e.options].map(o=>o.label):null}));
  const tables=[...document.querySelectorAll('table')].filter(visible).map(t=>({caption:text(t.caption),headers:[...t.querySelectorAll('th')].map(text),rows:[...t.querySelectorAll('tr')].map(r=>[...r.querySelectorAll('td')].map(text)).filter(r=>r.length)}));
  // A filtered structural outline gives the model enough information to propose
  // extraction selectors. It excludes scripts, URLs, attributes holding values,
  // hidden nodes, and the contents of editable elements.
  const outline=[...document.querySelectorAll('main,article,section,h1,h2,h3,p,dl,dt,dd,table,tr,th,td,a,span,strong')].filter(e=>visible(e)&&!e.closest('input,textarea,[contenteditable=true]')).slice(0,260).map(e=>selector(e)+' '+(e.children.length>3?'':text(e).slice(0,160))).join('\n');
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);const visibleText=[];let node;
  while(node=walker.nextNode()){const parent=node.parentElement;if(parent&&visible(parent)&&!parent.closest('script,style,input,textarea,select,[contenteditable=true]'))visibleText.push(node.textContent)}
  return {title:document.title,headings:[...document.querySelectorAll('h1,h2')].filter(visible).map(text),fields,controls,tables,dialog:[...document.querySelectorAll('dialog[open],[role=dialog][aria-modal=true]')].some(visible),loading:[...document.querySelectorAll('[aria-busy=true],[role=progressbar],[role=status]')].some(e=>visible(e)&&(e.getAttribute('aria-busy')==='true'||e.getAttribute('role')==='progressbar'||/loading/i.test(text(e)))),text:visibleText.join(' ').replace(/\s+/g,' ').slice(0,16000),structure:outline};
}
