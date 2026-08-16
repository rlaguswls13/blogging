/**
 * TECH LOG - Unified Site Theme JS Engine (v3.2.0)
 * Fully Extracted & Externalized JS Engine
 * 1. Immediate Label Redirect Enforcer
 * 2. Dynamic Category Modal Toggle Engine (Open / Close)
 * 3. Title Typography & Grid Standardizer
 * 4. 5-Page Block Numbered Pager Engine
 */

// Immediate Label Redirect Execution
(function() {
  var path = window.location.pathname;
  if (path === '/label' || path === '/label/') {
    window.location.replace('/search/label?max-results=4');
  } else if (path.indexOf('/label/') === 0) {
    var category = path.substring(7);
    window.location.replace('/search/label/' + category + '?max-results=4');
  }
})();

(function() {
  'use strict';

  var currentTagsData = [];

  // =========================================================
  // 1. Dynamic Category Modal Injector & Global Toggle Methods
  // =========================================================
  function ensureCategoriesModalExists() {
    var existingModal = document.getElementById('categories-modal');
    if (existingModal) return existingModal;

    var modalDiv = document.createElement('div');
    modalDiv.id = 'categories-modal';
    modalDiv.className = 'modal-overlay';
    modalDiv.setAttribute('style', 'display: none !important; visibility: hidden !important; opacity: 0 !important;');
    modalDiv.innerHTML = 
      '<div class="modal-box">' +
        '<div class="modal-header">' +
          '<h3>전체 카테고리</h3>' +
          '<button class="modal-close-btn" id="modal-close-btn-x" type="button" onclick="if(window.closeCategoriesModal) window.closeCategoriesModal(); return false;">×</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<div class="devlog-tags-popup" id="modal-tags-container"></div>' +
        '</div>' +
      '</div>';
    
    document.body.appendChild(modalDiv);

    modalDiv.addEventListener('click', function(e) {
      if (e.target === modalDiv) {
        window.closeCategoriesModal();
      }
    });

    return modalDiv;
  }

  window.showCategoriesModal = function() {
    var modal = ensureCategoriesModalExists();
    if (!modal) return;
    if (modal.parentElement !== document.body) {
      document.body.appendChild(modal);
    }
    
    var modalContainer = document.getElementById('modal-tags-container');
    if (!modalContainer) return;

    if (!currentTagsData || currentTagsData.length === 0) {
      var widget = document.getElementById('Label1') || document.querySelector('.widget.Label') || document.querySelector('[id^="Label"]');
      if (widget) {
        var container = widget.querySelector('.widget-content') || widget;
        var anchors = Array.from(container.querySelectorAll('a'));
        currentTagsData = anchors.map(function(a) {
          return { name: a.textContent.trim(), url: a.getAttribute('href') };
        });
      }
    }

    modalContainer.innerHTML = '';
    (currentTagsData || []).forEach(function(tag) {
      var tagEl = document.createElement('a');
      tagEl.href = tag.url;
      tagEl.className = 'tech-tag';
      tagEl.textContent = tag.name;
      tagEl.style.display = 'inline-flex';
      if (tag.count) {
        var countEl = document.createElement('span');
        countEl.className = 'label-count';
        countEl.style.marginLeft = '4px';
        countEl.style.fontWeight = '700';
        countEl.style.color = 'var(--primary-color, #2563eb)';
        countEl.textContent = '(' + tag.count + ')';
        tagEl.appendChild(countEl);
      }
      modalContainer.appendChild(tagEl);
    });

    modal.className = 'modal-overlay active';
    modal.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(6px) !important; align-items: center !important; justify-content: center !important; z-index: 999999 !important; padding: 1rem !important;';
    document.body.style.overflow = 'hidden';
  };

  window.closeCategoriesModal = function() {
    var modal = document.getElementById('categories-modal');
    if (modal) {
      modal.className = 'modal-overlay';
      modal.style.cssText = 'display: none !important; visibility: hidden !important; opacity: 0 !important;';
      document.body.style.overflow = '';
    }
  };

  function initCategoryTagsLimit() {
    ensureCategoriesModalExists();

    var widget = document.getElementById('Label1') || document.querySelector('.widget.Label') || document.querySelector('[id^="Label"]');
    if (!widget) return;

    var container = widget.querySelector('.widget-content') || widget;
    if (!container || container.querySelector('.devlog-tags')) return;

    var anchors = Array.from(container.querySelectorAll('a'));
    if (anchors.length === 0) return;

    var tagsData = [];
    anchors.forEach(function(a) {
      var rawText = a.textContent.trim();
      if (!rawText) return;

      var name = rawText;
      var count = "";
      
      var match = rawText.match(/(.+?)\s*\((\d+)\)$/);
      if (match) {
        name = match[1].trim();
        count = match[2];
      } else {
        var countSpan = a.querySelector('.label-count, .count') || (a.nextElementSibling && a.nextElementSibling.className && a.nextElementSibling.className.indexOf('count') !== -1 ? a.nextElementSibling : null);
        if (countSpan) {
          count = countSpan.textContent.replace(/[()]/g, '').trim();
          name = rawText.replace(countSpan.textContent, '').trim();
        }
      }

      tagsData.push({
        name: name,
        count: count,
        url: a.getAttribute('href')
      });
    });

    if (tagsData.length === 0) return;

    // 카테고리 정렬: 글 수 내림차순 -> 이름 오름차순
    tagsData.sort(function(a, b) {
      var countA = a.count ? parseInt(a.count, 10) : 0;
      var countB = b.count ? parseInt(b.count, 10) : 0;
      if (countA !== countB) return countB - countA;
      return a.name.localeCompare(b.name, 'ko', { sensitivity: 'base' });
    });

    currentTagsData = tagsData;

    // 기존 내용 비우고 모던 devlog-tags 칩 박스로 렌더링
    container.innerHTML = '';
    var tagsBox = document.createElement('div');
    tagsBox.className = 'devlog-tags';
    container.appendChild(tagsBox);

    // 상위 8개만 사이드바에 렌더링하고 나머지는 '...' 모달 팝업으로 제공
    tagsData.forEach(function(tag, idx) {
      if (idx < 8) {
        var tagEl = document.createElement('a');
        tagEl.href = tag.url;
        tagEl.className = 'tech-tag';
        tagEl.textContent = tag.name;
        if (tag.count) {
          var cEl = document.createElement('span');
          cEl.className = 'label-count';
          cEl.style.marginLeft = '4px';
          cEl.style.fontWeight = '700';
          cEl.style.color = 'var(--primary-color, #2563eb)';
          cEl.textContent = '(' + tag.count + ')';
          tagEl.appendChild(cEl);
        }
        tagsBox.appendChild(tagEl);
      }
    });

    // 8개 초과 시 '...' 모달 더보기 버튼 렌더링 (9번째 위치에 배치의 팝업 열기 버튼)
    if (tagsData.length > 8) {
      var moreBtn = document.createElement('button');
      moreBtn.type = 'button';
      moreBtn.className = 'tech-tag-more-btn';
      moreBtn.id = 'tech-tag-more-btn';
      moreBtn.textContent = '...';
      moreBtn.setAttribute('onclick', 'var m=document.getElementById("categories-modal"); if(m){ m.style.cssText="display: flex !important; visibility: visible !important; opacity: 1 !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(6px) !important; align-items: center !important; justify-content: center !important; z-index: 999999 !important; padding: 1rem !important;"; m.classList.add("active"); } if(window.showCategoriesModal) window.showCategoriesModal(); return false;');
      
      moreBtn.onclick = function(e) {
        if (e) {
          e.preventDefault();
          e.stopPropagation();
        }
        var m = document.getElementById('categories-modal');
        if (m) {
          m.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(6px) !important; align-items: center !important; justify-content: center !important; z-index: 999999 !important; padding: 1rem !important;';
          m.classList.add('active');
        }
        if (window.showCategoriesModal) {
          window.showCategoriesModal();
        }
        return false;
      };

      tagsBox.appendChild(moreBtn);
    }
  }

  // =========================================================
  // 2. Strict 4-Card Grid Standardizer & 5-Page Block Numbered Pager Engine
  // =========================================================
  var postPerPage = 4;   // 한 페이지당 정확히 글 4개만 노출
  var pageBlockSize = 5; // 한 번에 표시할 숫자 페이지 번호 개수 (5개 단위)
  var allPosts = [];
  var currentPage = 1;

  function enforceInitial4CardGrid() {
    var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts, .tech-featured-grid');
    if (!container) return;

    var cards = Array.from(container.children).filter(function(child) {
      return child.classList.contains('post-card') || child.classList.contains('tech-post-card') || child.tagName === 'ARTICLE';
    });

    if (cards.length > postPerPage && allPosts.length === 0) {
      for (var i = postPerPage; i < cards.length; i++) {
        cards[i].style.display = 'none';
      }
    }
  }

  function formatBloggerDate(dateStr) {
    if (!dateStr) return '';
    try {
      var d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return (d.getMonth() + 1) + '월 ' + d.getDate() + ', ' + d.getFullYear();
    } catch(e) {
      return dateStr;
    }
  }

  function renderPage(page) {
    var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts, .tech-featured-grid');
    if (!container) return;

    currentPage = page;
    var totalPages = Math.ceil(allPosts.length / postPerPage);
    if (page < 1) currentPage = 1;
    if (page > totalPages) currentPage = totalPages;

    var startIdx = (currentPage - 1) * postPerPage;
    var endIdx = startIdx + postPerPage;
    var pagePosts = allPosts.slice(startIdx, endIdx);

    container.innerHTML = '';
    pagePosts.forEach(function(post) {
      var article = document.createElement('article');
      article.className = 'post-card tech-post-card';
      
      var badgeCat = (post.labels && post.labels.length > 0) ? post.labels[0] : 'TECH';
      var tagsHtml = '';
      if (post.labels && post.labels.length > 0) {
        tagsHtml = '<div class="devlog-tags post-tags">';
        post.labels.slice(0, 4).forEach(function(lbl) {
          tagsHtml += '<a class="tech-tag" href="/search/label/' + encodeURIComponent(lbl) + '?max-results=4">' + lbl + '</a>';
        });
        tagsHtml += '</div>';
      }

      var formattedDate = formatBloggerDate(post.published);

      article.innerHTML = 
        '<div class="post-card-body tech-post-body">' +
          '<span class="post-category-badge tech-post-category">' + badgeCat + '</span>' +
          '<h2 class="post-card-title"><a href="' + post.url + '">' + post.title + '</a></h2>' +
          tagsHtml +
        '</div>' +
        '<div class="post-card-meta tech-post-meta">' +
          '<span>📅 ' + formattedDate + '</span>' +
        '</div>';
      
      container.appendChild(article);
    });

    render5BlockPagerControls(totalPages);

    window.scrollTo({
      top: container.offsetTop - 100,
      behavior: 'smooth'
    });
  }

  function render5BlockPagerControls(totalPages) {
    var pager = document.getElementById('blog-pager');
    if (!pager) return;

    if (totalPages <= 1) {
      pager.style.display = 'none';
      return;
    }

    pager.style.display = 'flex';

    var currentBlock = Math.ceil(currentPage / pageBlockSize);
    var startPage = (currentBlock - 1) * pageBlockSize + 1;
    var endPage = Math.min(totalPages, startPage + pageBlockSize - 1);

    var html = '<div class="tech-pagination-numbers" style="display:inline-flex;gap:0.5rem;align-items:center;">';

    if (startPage > 1) {
      var prevBlockTarget = startPage - 1;
      html += '<button class="page-btn prev-block-btn" data-page="' + prevBlockTarget + '">« 이전</button>';
    } else {
      html += '<button class="page-btn prev-block-btn disabled" style="opacity:0.4;cursor:not-allowed;" disabled>« 이전</button>';
    }

    for (var p = startPage; p <= endPage; p++) {
      var activeClass = p === currentPage ? ' active' : '';
      var activeStyle = p === currentPage ? ' style="background:var(--primary-color, #2563eb);color:#ffffff;font-weight:700;"' : '';
      html += '<button class="page-btn num-btn' + activeClass + '" data-page="' + p + '"' + activeStyle + '>' + p + '</button>';
    }

    if (endPage < totalPages) {
      var nextBlockTarget = endPage + 1;
      html += '<button class="page-btn next-block-btn" data-page="' + nextBlockTarget + '">다음 »</button>';
    } else {
      html += '<button class="page-btn next-block-btn disabled" style="opacity:0.4;cursor:not-allowed;" disabled>다음 »</button>';
    }

    html += '</div>';
    pager.innerHTML = html;

    var buttons = pager.querySelectorAll('.page-btn[data-page]');
    buttons.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var targetP = parseInt(btn.getAttribute('data-page'), 10);
        if (targetP && targetP !== currentPage) {
          renderPage(targetP);
        }
      });
    });
  }

  function getSearchFilterCriteria() {
    if (!window.location.search) return null;
    var urlParams = new URLSearchParams(window.location.search);
    var q = urlParams.get('q');
    if (!q) return null;

    q = decodeURIComponent(q).trim();
    if (!q) return null;

    var targetLabels = [];
    var keywords = [];

    var parts = q.split(/\s+OR\s+|\s+/i);
    parts.forEach(function(part) {
      part = part.trim();
      if (part.indexOf('label:') === 0) {
        var labelName = part.substring(6).replace(/^["']|["']$/g, '').trim();
        if (labelName) targetLabels.push(labelName.toLowerCase());
      } else if (part) {
        keywords.push(part.toLowerCase());
      }
    });

    return {
      labels: targetLabels,
      keywords: keywords,
      rawQuery: q
    };
  }

  function getTargetFilterLabel() {
    var pathname = window.location.pathname;
    var search = window.location.search;

    // 1. /search/label/라벨명 처리
    if (pathname.indexOf('/search/label/') !== -1) {
      var parts = pathname.split('/search/label/');
      if (parts.length > 1 && parts[1]) {
        var labelStr = parts[1].split('?')[0];
        return decodeURIComponent(labelStr).trim().toLowerCase();
      }
    }

    // 2. /search?q=label:라벨명 처리
    if (search && search.indexOf('q=') !== -1) {
      var urlParams = new URLSearchParams(search);
      var q = urlParams.get('q');
      if (q) {
        q = decodeURIComponent(q).trim().toLowerCase();
        if (q.indexOf('label:') !== -1) {
          return q;
        }
      }
    }

    return null;
  }

  window.initBloggerFeedPagination = function(json) {
    var entries = (json.feed && json.feed.entry) ? json.feed.entry : [];
    allPosts = [];

    entries.forEach(function(entry) {
      var title = entry.title ? entry.title.$t : '';
      var published = entry.published ? entry.published.$t : '';
      var url = '';
      if (entry.link) {
        for (var i = 0; i < entry.link.length; i++) {
          if (entry.link[i].rel === 'alternate') {
            url = entry.link[i].href;
            break;
          }
        }
      }
      var labels = [];
      if (entry.category) {
        entry.category.forEach(function(cat) {
          if (cat.term) labels.push(cat.term);
        });
      }

      allPosts.push({
        title: title,
        published: published,
        url: url,
        labels: labels
      });
    });

    var targetFilter = getTargetFilterLabel();
    if (targetFilter) {
      var activePosts = [];
      allPosts.forEach(function(post) {
        var lowerPostLabels = post.labels.map(function(l) { return l.toLowerCase(); });
        var matches = false;

        if (targetFilter.indexOf('basics') !== -1 || targetFilter.indexOf('기초') !== -1) {
          var basicsGroup = ['basics', '기초', 'database', 'rdbms', 'sql', 'nosql', 'gof', 'design patterns', 'java', 'mvc'];
          for (var bIdx = 0; bIdx < basicsGroup.length; bIdx++) {
            if (lowerPostLabels.indexOf(basicsGroup[bIdx]) !== -1) {
              matches = true;
              break;
            }
          }
        } else if (targetFilter.indexOf('advanced') !== -1 || targetFilter.indexOf('응용') !== -1 || targetFilter.indexOf('실무') !== -1) {
          var advGroup = ['advanced', '응용', '실무', 'system architecture', 'microservices', 'kafka', 'redis', 'distributed lock', 'concurrency', 'saga pattern', 'software engineering', 'software architecture', 'spring aop', 'cg-lib', 'aspectj', 'spring boot'];
          for (var aIdx = 0; aIdx < advGroup.length; aIdx++) {
            if (lowerPostLabels.indexOf(advGroup[aIdx]) !== -1) {
              matches = true;
              break;
            }
          }
        } else if (targetFilter.indexOf('trends') !== -1 || targetFilter.indexOf('트렌드') !== -1) {
          var trendGroup = ['trends', '트렌드', 'ai agent', 'graphrag', 'ai framework', 'llm', 'llm agent', 'kubernetes', 'cloud-native', 'devops', 'http3', 'quic', 'autogen'];
          for (var tIdx = 0; tIdx < trendGroup.length; tIdx++) {
            if (lowerPostLabels.indexOf(trendGroup[tIdx]) !== -1) {
              matches = true;
              break;
            }
          }
        } else {
          // 기타 일반 단일 라벨 필터링
          if (lowerPostLabels.indexOf(targetFilter) !== -1) {
            matches = true;
          }
        }

        if (matches) {
          activePosts.push(post);
        }
      });

      allPosts = activePosts;
    }

    if (allPosts.length > 0) {
      renderPage(1);
    } else if (targetFilter) {
      var postsContainer = document.querySelector('.blog-posts') || document.querySelector('.main-content') || document.getElementById('main');
      if (postsContainer) {
        postsContainer.innerHTML = '<div style="text-align:center; padding: 4rem 1rem; color: #64748b; background: #ffffff; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"><h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; color:#1e293b;">해당 카테고리의 포스팅이 없습니다</h3><p style="font-size: 0.95rem;">카테고리 라벨: "' + targetFilter + '"</p></div>';
      }
    }
  };

  // =========================================================
  // 5. Event Listeners and Initialization
  // =========================================================
  document.addEventListener("DOMContentLoaded", function() {
    ensureCategoriesModalExists();
    initCategoryTagsLimit();

    enforceInitial4CardGrid();
    setTimeout(enforceInitial4CardGrid, 300);
    setTimeout(enforceInitial4CardGrid, 1000);

    if (window.location.pathname.indexOf('/20') !== 0 || window.location.pathname.indexOf('.html') === -1) {
      var script = document.createElement('script');
      script.src = '/feeds/posts/summary?alt=json-in-script&max-results=150&callback=initBloggerFeedPagination';
      document.body.appendChild(script);
    }

    var mermaidEls = document.querySelectorAll('.mermaid');
    if (mermaidEls.length > 0 && typeof mermaid !== 'undefined') {
      mermaid.initialize({
        startOnLoad: true,
        theme: 'neutral',
        securityLevel: 'loose',
        flowchart: { useMaxWidth: true, htmlLabels: true }
      });
    }
  });

  // Global Event Delegation for Category Tag More Button (...)
  document.addEventListener('click', function(e) {
    var target = e.target;
    if (target && (target.classList.contains('tech-tag-more-btn') || target.id === 'tech-tag-more-btn')) {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      var modal = document.getElementById('categories-modal');
      if (modal) {
        modal.className = 'modal-overlay active';
        modal.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(6px) !important; align-items: center !important; justify-content: center !important; z-index: 999999 !important; padding: 1rem !important;';
        document.body.style.overflow = 'hidden';
      }
      if (window.showCategoriesModal) {
        window.showCategoriesModal();
      }
      return false;
    }
  }, true);
})();
