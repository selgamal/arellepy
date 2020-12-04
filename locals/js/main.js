// helper for loading files
function loadJSON(file, callback) {
  var j = new XMLHttpRequest();
  j.overrideMimeType("application/json");
  j.open("GET", file, true);
  j.onreadystatechange = function() {
    if (j.readyState == 4 && j.status == "200") {
      callback(j.responseText);
    }
  };
  j.send();
};

function getRoute(route, callback)
{
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() { 
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
            callback(xmlHttp.responseText);
    }
    xmlHttp.open("GET", route, true); 
    xmlHttp.send();
}



// Close currently focused element if close-able
function closeAllOpen() {
  var actv = document.activeElement;
  var el = actv.closest(".open");
  if (el) {
    el.classList.remove("open");
    fixTabIndex(el, "-1", "a:not(.txt-color), input.slider");
  } else {
    var open_elts = document.getElementsByClassName("open");
    if (open_elts) {
      for (let i = 0; i < open_elts.length; i++) {
        var el = open_elts[i];
        el.classList.remove("open");
        fixTabIndex(el, "-1", "a, input.slider");
      }
    }
  }
}

// sync keyboard and mouse navigation
function Key_mouse_handler(x) {
  zz = x;
  classes = x.target.classList;
  dd_clicked = classes.contains("dropdown-component");
  if (x.type == "keyup") {
    var lastKeyPress = x.key;
    //handle key presses
    switch (lastKeyPress) {
      case "Escape":
        closeAllOpen();
        // other stuff
        break;
      case "Enter":
        if (dd_clicked) {
          ddMenuOpen_Close(x.target.dataset.for);
        }
        // other stuff
        break;
      // other stuff
      case "x":
        // console.log(x.key);
        // other stuff
        break;
      default:
        if (!dd_clicked) {
          closeAllOpen();
        }
    }
  } else if (x.type == "mouseup") {
    //handel dropdown menus
    if (dd_clicked) {
      ddMenuOpen_Close(x.target.dataset.for);
    } else {
      closeAllOpen();
    }
    //handle other mouseup here
    // document.activeElement.blur(); // deals with focus when using mouse clicks
  } 
  //   console.log(document.activeElement);
}

function ddMenuOpen_Close(f) {
  a = document.getElementById(f);
  if (a) {
    var b = a.classList.contains("open");
    if (!b) {
      fixTabIndex(a, "", "a, input.slider");
      a.classList.add("open");
    } else if (b) {
      a.classList.remove("open");
      fixTabIndex(a, "-1", "a, input.slider");
    }
  }
}

function fixTabIndex(el, n, tg) {
  var elts = el.querySelectorAll(tg);
  for (let i = 0; i < elts.length; i++) {
    elts[i].setAttribute("tabindex", n);
  }
}

// Toggle checkbox
function toggleChk(chkId) {
  var el = document.getElementById(chkId)
  var state = el.checked;
  el.checked = !state
  
}

//function to create theme menus
function createThemeMenu() {
  for (let n = 0; n < 6; n++) {
    var i = Object.keys(palettes)[n];
    var tmp = document.getElementById("theme-link-template").content.cloneNode(true);
    var item = tmp.querySelector(".dropdown-item.dropdown-component.thm-color");
    if (palettes.hasOwnProperty(i)) {
      const el = palettes[i];
      var name = el[0];
      item.setAttribute("id", i);
      rect = item.getElementsByTagName("rect")[0];
      rect.style.fill = el[1][0][1];
      var txt = item.getElementsByTagName('span')[0];
      txt.appendChild(document.createTextNode(name));
      var parent = document.getElementById("themes");
      var find_me = !!document.getElementById(i);
      if (!find_me) {
        parent.appendChild(item);
      }
    }
  }

  max_n = Object.keys(palettes).length;
  var n = Math.floor(Math.random() * max_n + 0);
  var tmp2 = document.getElementById("theme-link-template").content.cloneNode(true);
  var randItem = tmp2.querySelector(".dropdown-item.dropdown-component.thm-color");
  var thm_n = Object.keys(palettes)[n];
  var el_n = palettes[thm_n];
  var name_n = el_n[0];
  randItem.setAttribute("id", "thm-RR");
  randItem.setAttribute("onClick", "changePaletteRand()");
  var rect = randItem.getElementsByTagName("rect")[0];
  rect.style.fill = el_n[1][0][1];
  var txt_n = randItem.getElementsByTagName('span')[0]
  txt_n.appendChild(document.createTextNode("Random: " + name_n));
  var parent_n = document.getElementById("themes");
  parent_n.appendChild(randItem);
}

function changePalette(id) {
  let root = document.documentElement;
  const pl = palettes[id][1];
  for (let i = 0; i < pl.length; i++) {
    const el = pl[i];
    root.style.setProperty(el[0], el[1]);
  }
  $(".dropdown-item.thm-color.active").removeClass("active");
  document.getElementById(id).classList.add("active");
}

function changeTxt_color(val, id) {
  let root = document.documentElement;
  const txt = txt_colors[val];
  if (id == "txt-light") {
    root.style.setProperty("--text-color-light", txt);
  } else {
    root.style.setProperty("--text-color-dark", txt);
  }
}

function changePaletteRand() {
  var r = document.getElementById("thm-RR");
  var n = Math.floor(Math.random() * max_n + 0);
  var thm_n = Object.keys(palettes)[n];
  r.getElementsByTagName("span")[0].innerText = "Random: " + palettes[thm_n][0];
  r.getElementsByTagName("rect")[0].style.fill = palettes[thm_n][1][0][1];
  let root = document.documentElement;
  const plx = palettes[thm_n][1];
  for (let i = 0; i < plx.length; i++) {
    const el = plx[i];
    root.style.setProperty(el[0], el[1]);
  }
  $(".dropdown-item.thm-color.active").removeClass("active");
  document.getElementById("thm-RR").classList.add("active");
}

function OpenDialog(id) {
  $('#'+id ).dialog( "open" );
};

function makeSelectFolderOption(parent, txt, slct) {
  var o = document.createElement('option');
  o.setAttribute('value', txt);
  var t = document.createTextNode(txt);
  o.selected = slct;
  o.appendChild(t);
  parent.appendChild(o);
}

function openDirExplorer() {
  getRoute('/selectLookinFolders', function(txt) {
    if(txt=='') return;
    if(!$('#select-folders-dialog').dialog('isOpen')) return;
    var n = true;
    var s = document.getElementById('folders-select-list');
    Array.prototype.slice.call(s.options).map(function(x) {
      if(x.text == txt) {
        x.selected = true;
        n = false
      } else {
        x.selected = false;
      }
    })

    if(n) {
      makeSelectFolderOption(s, txt, true)
    };
  });
}

function removeLookinFolder(slctd) {
  var o = document.getElementById("folders-select-list").options;
  Array.prototype.slice.call(o).map(function(x) {
    if (slctd) {
      if (x.selected) {
        x.remove();
      }
    } else {
      x.remove()
    }
  });
}



function sendLookinFolders() {
  var xmlHttp = new XMLHttpRequest();
  xmlHttp.open("POST", '/changeLookinFolders', true); 
  xmlHttp.setRequestHeader('Content-Type', 'application/json');
  var s = document.getElementById("folders-select-list").options;
  var f = Array.prototype.slice.call(s).map(function(x) {
      return x.text;
    });
  xmlHttp.send(JSON.stringify(f));
  xmlHttp.onreadystatechange = function() { 
    if (xmlHttp.readyState == 4 && xmlHttp.status == 200) {
      if (xmlHttp.responseText) {
        document.getElementById('refresh-btn').classList.add('updatable')
      }
      // console.log(JSON.parse(xmlHttp.responseText));
    }

       
}

}

function edgarLink(el) {
  var p = el.closest('.filing-card').dataset;
  var d = new URLSearchParams(
    {
      cik:p['cik'],
      formType:p['form'],
      reportDate:p['periodEnd'],
      filingDate:p['filingDate'],
      route:p['route']
    }
  );
  // console.log(d.toString())
  window.open('/EdgarLink?'+d.toString())
}

function saveLookinFolders() {
  // Close dialog
  $('#select-folders-dialog').dialog('close')

  // instruct server to save new paths
  sendLookinFolders()

}


// prep document
$(document).ready(function() {

  // load theme palettes
  loadJSON("locals/updatable/all_pals_sorted.json", function(txt) {
    palettes = JSON.parse(txt);
    // load text colors
    loadJSON("locals/updatable/txt_colors.json", function(txt) {
      txt_colors = JSON.parse(txt);
    });
    createThemeMenu();
  });

  // initialize folder select dialog
  $("#select-folders-dialog").dialog({
    autoOpen: false,
    dialogClass: "select-folders-dialog",
    height:200,
    width:450,
    resizable: false,
    buttons: {
      "addFolders": {
        text: 'Add Folders',
        id: "add-folders-btn",
        click: openDirExplorer,
        class: 'btn'
      },
      "removeFolders" : {
        text: 'Remove Selected',
        id: "remove-folders-btn",
        click: function() {
          removeLookinFolder(true)
        },
        class: 'btn'
      },
      'ok' : {
        text: 'OK',
        id: 'ok-folders-btn',
        click: saveLookinFolders,
        class: 'btn'
      }
    }
  });

  // Initially prep look in folders list
  getRoute('/getLookinFolders', function(paths) {
    var p = JSON.parse(paths);
    if (p.length > 0) {
      var s = document.getElementById('folders-select-list');
      for (let i = 0; i < p.length; i++) {
        makeSelectFolderOption(s, p[i], false);
      }
    }
  });


  // on close of dialog using corner x (cancel)
  $(".select-folders-dialog .ui-dialog-titlebar-close").click(function() {
    getRoute('/getLookinFolders', function(paths) {
      var p = JSON.parse(paths);
      var s = document.getElementById('folders-select-list');
      var o = s.options
      removeLookinFolder(false)
      if (p.length > 0) {
        for (let i = 0; i < p.length; i++) {
          makeSelectFolderOption(s, p[i], false);
        }
      }
    });
  });

  // add Filings Cards if viewer initialized with looking folders
  refreshCards();

  var tabs = document.getElementsByClassName("nav-link");
  for (let i = 0; i < tabs.length; i++) {
    tabs[i].setAttribute("onclick", "selectTab(this)");
  };

  $("#filings-titles-ribbon").sortable()


  document.getElementById("home-tab").click();
});

function jumpToTab(id, el) {
  var p = el.closest('.filing-card');
  var cls = el.classList.contains('disabled');
  if (!cls) {
    var navs = Array.prototype.slice.call(document.querySelectorAll(".filing-nav-tab")).map(function (x) { return x.id });
    if (navs.includes(p.id+ '-nav')) {
      document.getElementById(id).click();
      document.getElementById(p.id + '-nav').focus();
      document.getElementById(p.id + '-nav').querySelector(".filing-name").click();
    } else {
      var tmp = document.getElementById("filing-nav-tab-template").content.cloneNode(true);
      var t = tmp.querySelector(".filing-nav-tab");
      var l = el.dataset.link;
      var txt = p.dataset.filer + (p.dataset.fy ||  p.dataset.year ?  ' (':'') + p.dataset.fy.toUpperCase() + p.dataset.year + (p.dataset.fy ||  p.dataset.year ?  ' )':'');
      var title_a = p.dataset.filer 
      var title_b = p.dataset.form.toUpperCase() + (p.dataset.fy ||  p.dataset.year ?  ' (':'') + p.dataset.fy.toUpperCase() + p.dataset.year + (p.dataset.fy ||  p.dataset.year ?  ' )':'')
      var txt_n = document.createTextNode(txt);
      t.querySelector(".filing-name").appendChild(txt_n);
      t.id = p.id + '-nav';
      t.dataset.for = p.id + '-frame';
      t.dataset.selector = p.id + '-selector'
      t.dataset.link = l
      t.dataset.titleA = title_a
      t.dataset.titleB = title_b
      t.dataset.primeDoc = p.dataset.primeDoc
      t.dataset.inlinexbrl = p.dataset.inlinexbrl
      var ribbon = document.getElementById("filings-titles-ribbon");
      ribbon.appendChild(t);
      document.getElementById(id).click();
      document.getElementById(p.id + '-nav').focus();
      document.getElementById(p.id + '-nav').querySelector(".filing-name").click();
      ribbon.scrollLeft = ribbon.scrollWidth

    }
  }
}


function showFrame(el) {
  var f = el.dataset.for
  var s = el.dataset.selector
  var l = el.dataset.link
  var n = el.id
  var frames = Array.prototype.slice.call(document.getElementsByClassName('filing-frame'));
  var selectors = Array.prototype.slice.call(document.getElementsByClassName('filer-name-report-type'))
  var navs = Array.prototype.slice.call(document.getElementsByClassName("filing-nav-tab"));
  var title = document.getElementById('filer-name');
  selectors.map(function(x) { x.classList.add('hide-selector')});
  
  // Upadate title
  title.querySelector("#filer-name-main").innerText = el.dataset.titleA
  title.querySelector("#filer-name-form").innerText = el.dataset.titleB
  document.getElementById("filer-none").style.display = 'none'
  title.style.display = 'block'

  // Make iframe and selector if do not exits
  var iframeIds = frames.map(function(x){return x.id});
  selectors.map
  if (iframeIds.includes(f)) {
    frames.map(function(x) {
      if(x.id == f) {
        x.classList.remove('hide-frame')
        document.getElementById(s).classList.remove('hide-selector')
      } else {
        x.classList.add('hide-frame')
      }
    });
  } else {
    frames.map(function(x) { x.classList.add('hide-frame') });
    // Make report type selector
    console.log(el.dataset)
    var tmp1 = document.getElementById("report-type-selector-template").content.cloneNode(true);
    var t1 = tmp1.querySelector(".filer-name-report-type");
    t1.id = s
    t1.dataset.iframe = f
    t1.options[0].value = l + "/" + el.dataset.primeDoc;
    t1.options[1].value = l + "/FilingSummary.htm";
    t1.options[2].value = (el.dataset.inlinexbrl=="yes" ? "/home/ix.html?xbrl=true&doc=":"") + l + "/" + el.dataset.primeDoc;
    

    // Make iframe
    var tmp2 = document.getElementById("filing-frame-template").content.cloneNode(true);
    var t2 = tmp2.querySelector(".filing-frame");
    t2.id = f;
    t2.src = t1.options[0].value;
    var filer = document.getElementById("filer-name")
    var beforeEl = filer.querySelector('#report-type-info')
    filer.insertBefore(t1, beforeEl);
    document.getElementById("filings-tab-content").appendChild(t2);
  };

  // Selected nav tab
  navs.map(function(x) {
    if(x.id == n) {
      x.querySelector('.filing-name').classList.add('active')
    } else {
      x.querySelector('.filing-name').classList.remove('active')
    }
  });
  
}

function selectFrameType(link, frame, i, id) {
  var ifr = document.getElementById(frame);
  ifr.src = link;

}

function destroyFrame(el) {
  var frame = el.dataset.for
  var selector = el.dataset.selector
  var self = el.id
  var active = el.querySelector(".filing-name").classList.contains("active")
  if(active) {
    var title = document.getElementById('filer-name');
    document.getElementById("filer-name-main").innerText = ''
    document.getElementById("filer-name-form").innerText = ''
    // title.firstElementChild.innerText = ''
    // title.lastElementChild.innerText = ''
    title.style.display = 'none'
    if(el.nextElementSibling != null) {
      el.nextElementSibling.focus()
      el.nextElementSibling.querySelector(".filing-name").click()
    } else if(el.previousElementSibling != null & el.previousElementSibling.tagName == 'DIV') {
      el.previousElementSibling.focus()
      el.previousElementSibling.querySelector(".filing-name").click()
    } else {
      document.getElementById('filer-none').style.display = ''
    }
  }
  document.getElementById(frame).remove();
  document.getElementById(selector).remove();
  document.getElementById(self).remove();
}


// Select tabs
function selectTab(el) {
  if (!el.classList.contains("dropdown-link")) {
    var target = el.dataset.for;
    var tabs = document.getElementsByClassName("nav-link");
    for (let i = 0; i < tabs.length; i++) {
      tabs[i].classList.remove("active");
    }
    el.classList.add("active");
    var content = document.getElementsByClassName("tab-content");
    for (let i = 0; i < content.length; i++) {
      if (content[i].id == target) {
        content[i].classList.add("show");
      } else {
        content[i].classList.remove("show");
      }
    }
  }
}

// Create filing cards from template
function createCards(filingInfo) {
  // console.log(filingInfo)
  var tmp = document.getElementById("filing-card-template").content.cloneNode(true);
  var t = tmp.querySelector(".filing-card");
  for (var i in filingInfo) {
    if (i.startsWith('card-') || i=="dataAttrs") {
      if (i == "card-header") {
        var _txt = document.createTextNode(filingInfo[i]);
        t.getElementsByClassName(i)[0].appendChild(_txt);
      } else if(i == "dataAttrs") {
        var d = Object.keys(t.dataset)
        // d.forEach((a, l) => console.log(a + "--" + l));
        d.forEach((a, l) => t.dataset[a] = filingInfo[i][l].toLocaleLowerCase());
      } else if(i == "card-sourceFileLoc") {
        //t.getElementsByClassName(i)[0].href = filingInfo[i][1]
        var _txt = document.createTextNode('Edgar Filing');
        t.getElementsByClassName(i)[0].appendChild(_txt)
      } else {
        var _lab = document.createTextNode(filingInfo[i][0] + (filingInfo[i][0] ? ":" : "") );
        var _val = document.createTextNode(filingInfo[i][1]);
        var _txt = document.createTextNode(_val);
        t.querySelectorAll('.' + i + ' .card-info-lab')[0].appendChild(_lab);
        t.querySelectorAll('.' + i + ' .card-info-val')[0].appendChild(_val);
      };
    };
    var _id = t.dataset.cik + t.dataset.form + t.dataset.fy + t.dataset.year 
    t.setAttribute("id", _id.replace("-",""))
  }
  t.dataset.filer = filingInfo["card-header"]
  return t
}

function addFilingsCards(filingsList) {
  // fade_in_out("cards-overview");
  var cardsList = [];
  var n = 0;
  for(var i in filingsList) {
    var el = createCards(filingsList[i]);
    el.dataset.route = i;
    el.querySelector(".card-filing-menu").dataset.link = "/filing/"+ i
    cardsList[n] = el;
    n++;
  }
  cardsList.sort(function(a,b) {
    return a.dataset.cik - b.dataset.cik || new Date(b.dataset.periodEnd) - new Date(a.dataset.periodEnd)
  })
  var cards_ = Array.prototype.slice.call(document.getElementById("cards-overview").children).slice(1)
  if (cards_.length > 0) {
       for (i in cards_) {
        cards_[i].remove();
    }
  };
  for (let i = 0; i < cardsList.length; i++) {
    document.getElementById("cards-overview").appendChild(cardsList[i]); 
  };
  document.getElementById('refresh-btn').classList.remove('spinning')
  document.getElementById("cards-overview").style.opacity = 1
} 

function refreshCards() {
  document.getElementById('refresh-btn').classList.remove('updatable')
  document.getElementById('refresh-btn').classList.add('spinning')
  document.getElementById("cards-overview").style.opacity = 0;
  getRoute('/getLoc', function(txt) {
    var filings = JSON.parse(txt);
    addFilingsCards(filings);
  });
}

function sortfunc(el, v) {
  // console.log(el)
  var elt = el.dataset.for
  var s = el.dataset.sorted
  fade_in_out(elt)
  var x = Array.prototype.slice.call(
    document.getElementsByClassName("filing-card")
  );
  switch (v) {
    case 'date':
      if(s==0) {
        // console.log(s)
        x.sort(function(a, b) {
          return new Date(a.dataset.periodEnd) - new Date(b.dataset.periodEnd);
        });
        el.dataset.sorted = 1
      } else {
        x.reverse()
        el.dataset.sorted = 0
      }
      break;
    case 'cik':
      if(s==0) {
        x.sort(function(a, b) {
          return a.dataset.cik - b.dataset.cik;
        });
        el.dataset.sorted = 1

      } else {
        x.reverse()
        el.dataset.sorted = 0
      }
      break;
    case 'form':
      if(s==0) {
        x.sort(function(a, b) {
          if (a.dataset.form > b.dataset.form) return 1
          if (a.dataset.form < b.dataset.form) return -1
          return 0
        });
        el.dataset.sorted = 1

      } else {
        x.reverse()
        el.dataset.sorted = 0
      }
      break;
    case "name":
      if(s==0) {
        x.sort(function(a, b) {
          if (a.dataset.filer.toLowerCase() > b.dataset.filer.toLowerCase()) return 1
          if (a.dataset.filer.toLowerCase() < b.dataset.filer.toLowerCase()) return -1
          return 0
        });
        el.dataset.sorted = 1

      } else {
        x.reverse()
        el.dataset.sorted = 0
      }
      break;
  }
  for (let i = 0; i < x.length; i++) {
    document.getElementById("cards-overview").appendChild(x[i]);
  }
}

function fade_in_out(el) {
  var elt = document.getElementById(el)
  elt.style.opacity = 0
  setTimeout(function(){elt.style.opacity = 1},200)
}



//Global events
document.onkeyup = function(a) {
  Key_mouse_handler(a);
};

document.onmouseup = function(e) {
  Key_mouse_handler(e);

};


window.onresize = closeAllOpen;


// filter search
function searchCards(input) {
  var filter = input.toLowerCase();
  var data = document.getElementsByClassName("filing-card");
  for (var i = 0; i < data.length; i++) {
      a = Object.values(Object.assign({}, data[i].dataset));
      for (var w = 0; w < a.length; w++) {
        if (a[w].toLowerCase().indexOf(filter) > -1) {
          data[i].style.display = "";
          break;
        } else {
          data[i].style.display = "none";
        }
      }  
  }
}

function searchTerm(input, el) {
  var filter = input.toLowerCase();
  a = Object.values(Object.assign({}, el.dataset));
  for (var w = 0; w < a.length; w++) {
    if (a[w].toLowerCase().indexOf(filter) > -1) {
      var res = 1
      return res
    } else {
      var res = 0
    }
  }  
  return res
}

function searchCardsTerms(input) {
  document.getElementById('home-tab').click()
  var filter = input.split(" ");
  var data = document.getElementsByClassName("filing-card"); 
  for (var i = 0; i < data.length; i++) {
    var res = filter.map(function(t){ return searchTerm(t, data[i])})
    var match = res.every( function(x){ return x == 1} )
    if(match) {
      data[i].style.display = "";
    } else {
      data[i].style.display = "none";
    }
  }
}


function scrollFunc(el, sign) {
  var step = 2* ( el.scrollWidth / el.children.length);
  var pos = el.scrollLeft;
  if(sign == '+') {
    el.scrollLeft = pos + step
  } else if(sign == '-') {
    el.scrollLeft = pos - step
  }
  
}

