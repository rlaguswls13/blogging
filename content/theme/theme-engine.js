/**
 * TECH LOG - Unified Site Theme JS Engine (v25.0.0)
 * Complete rewrite with full inline tab filter & pagination engine
 */

// =========================================================
// 1. Label URL Redirect Enforcer
// =========================================================
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
  var postPerPage = 4;
  var pageBlockSize = 5;
  var allPosts = [];
  var currentPage = 1;

  // =========================================================
  // 2. URL Filter Label Parser
  // =========================================================
  function getTargetFilterLabel() {
    var pathname = window.location.pathname;
    var search = window.location.search;

    if (pathname.indexOf('/search/label/') !== -1) {
      var parts = pathname.split('/search/label/');
      if (parts.length > 1 && parts[1]) {
        var labelStr = parts[1].split('?')[0];
        return decodeURIComponent(labelStr).trim().toLowerCase();
      }
    }

    if (search && search.indexOf('q=') !== -1) {
      try {
        var urlParams = new URLSearchParams(search);
        var q = urlParams.get('q');
        if (q) {
          q = decodeURIComponent(q).trim().toLowerCase();
          if (q.indexOf('label:') !== -1) return q;
        }
      } catch(e) {}
    }

    return null;
  }

  // =========================================================
  // 3. Post Label Matching Engine
  // =========================================================
  function postMatchesFilter(post, targetFilter) {
    var lowerLabels = post.labels.map(function(l) { return l.toLowerCase(); });

    if (targetFilter.indexOf('basics') !== -1) {
      var basicsGroup = ['basics', '기초', 'database', 'rdbms', 'sql', 'nosql', 'gof', 'design patterns', 'java', 'mvc', 'btreeindex', 'coveringindex', 'operatingsystem', 'concurrency'];
      for (var i = 0; i < basicsGroup.length; i++) {
        if (lowerLabels.indexOf(basicsGroup[i]) !== -1) return true;
      }
      return false;
    }

    if (targetFilter.indexOf('advanced') !== -1) {
      var advGroup = ['advanced', '응용', '실무', 'system architecture', 'microservices', 'kafka', 'redis', 'distributed lock', 'concurrency', 'saga pattern', 'software engineering', 'software architecture', 'spring aop', 'cg-lib', 'aspectj', 'spring boot', 'msa', 'btreeindex', 'coveringindex', 'operatingsystem'];
      for (var j = 0; j < advGroup.length; j++) {
        if (lowerLabels.indexOf(advGroup[j]) !== -1) return true;
      }
      return false;
    }

    if (targetFilter.indexOf('trends') !== -1) {
      var trendGroup = ['trends', '트렌드', 'ai agent', 'graphrag', 'ai framework', 'llm', 'llm agent', 'kubernetes', 'cloud-native', 'devops', 'http3', 'quic', 'autogen'];
      for (var k = 0; k < trendGroup.length; k++) {
        if (lowerLabels.indexOf(trendGroup[k]) !== -1) return true;
      }
      return false;
    }

    // 단일 라벨 직접 매칭
    return lowerLabels.indexOf(targetFilter) !== -1;
  }

  // =========================================================
  // 4. Post Card HTML Builder
  // =========================================================
  function formatBloggerDate(dateStr) {
    if (!dateStr) return '';
    try {
      var d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return (d.getMonth() + 1) + '월 ' + d.getDate() + ', ' + d.getFullYear();
    } catch(e) { return dateStr; }
  }

  function buildPostCardHtml(post) {
    var categoryBadge = (post.labels && post.labels.length > 0) ? post.labels[0] : 'TECH';
    var tagsHtml = '';
    if (post.labels && post.labels.length > 0) {
      tagsHtml = '<div class="devlog-tags post-tags">';
      post.labels.slice(0, 4).forEach(function(lbl) {
        tagsHtml += '<a class="tech-tag" href="/search/label/' + encodeURIComponent(lbl) + '?max-results=4">' + lbl + '</a>';
      });
      tagsHtml += '</div>';
    }
    var dateFormatted = formatBloggerDate(post.published);

    return '<article class="post-card tech-post-card">' +
      '<div class="post-card-body tech-post-body">' +
        '<span class="post-category-badge tech-post-category">' + categoryBadge + '</span>' +
        '<h2 class="post-card-title"><a href="' + post.url + '">' + post.title + '</a></h2>' +
        tagsHtml +
      '</div>' +
      '<div class="post-card-meta tech-post-meta">' +
        '<span>📅 ' + dateFormatted + '</span>' +
      '</div>' +
    '</article>';
  }

  // =========================================================
  // 5. Pagination Controls
  // =========================================================
  function renderPaginationControls(totalPages) {
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
      html += '<button class="page-btn prev-block-btn" data-page="' + (startPage - 1) + '">« 이전</button>';
    } else {
      html += '<button class="page-btn prev-block-btn disabled" style="opacity:0.4;cursor:not-allowed;" disabled>« 이전</button>';
    }

    for (var p = startPage; p <= endPage; p++) {
      var activeClass = p === currentPage ? ' active' : '';
      var activeStyle = p === currentPage ? ' style="background:var(--primary-color, #2563eb);color:#ffffff;font-weight:700;"' : '';
      html += '<button class="page-btn num-btn' + activeClass + '" data-page="' + p + '"' + activeStyle + '>' + p + '</button>';
    }

    if (endPage < totalPages) {
      html += '<button class="page-btn next-block-btn" data-page="' + (endPage + 1) + '">다음 »</button>';
    } else {
      html += '<button class="page-btn next-block-btn disabled" style="opacity:0.4;cursor:not-allowed;" disabled>다음 »</button>';
    }

    html += '</div>';
    pager.innerHTML = html;

    pager.querySelectorAll('.page-btn[data-page]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var targetP = parseInt(btn.getAttribute('data-page'), 10);
        if (targetP && targetP !== currentPage) {
          window.renderPage(targetP);
        }
      });
    });
  }

  // =========================================================
  // 6. Core Page Renderer (Global)
  // =========================================================
  window.renderPage = function(page) {
    var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts, .tech-featured-grid');
    if (!container) return;

    currentPage = page;
    var totalPages = Math.ceil(allPosts.length / postPerPage);
    if (currentPage < 1) currentPage = 1;
    if (currentPage > totalPages) currentPage = totalPages;

    var startIdx = (currentPage - 1) * postPerPage;
    var pagePosts = allPosts.slice(startIdx, startIdx + postPerPage);

    var html = '';
    pagePosts.forEach(function(post) {
      html += buildPostCardHtml(post);
    });
    container.innerHTML = html;

    renderPaginationControls(totalPages);

    window.scrollTo({ top: container.offsetTop - 100, behavior: 'smooth' });
  };

  // =========================================================
  // 7. Main Feed Pagination Callback (Global)
  // =========================================================
  window.initBloggerFeedPagination = function(json) {
    var entries = (json.feed && json.feed.entry) ? json.feed.entry : [];
    allPosts = [];

    entries.forEach(function(entry) {
      var title = entry.title ? entry.title.$t : '';
      var published = entry.published ? entry.published.$t : '';
      var url = '';
      if (entry.link) {
        for (var i = 0; i < entry.link.length; i++) {
          if (entry.link[i].rel === 'alternate') { url = entry.link[i].href; break; }
        }
      }
      var labels = [];
      if (entry.category) {
        entry.category.forEach(function(cat) { if (cat.term) labels.push(cat.term); });
      }
      allPosts.push({ title: title, published: published, url: url, labels: labels });
    });

    var targetFilter = getTargetFilterLabel();
    if (targetFilter) {
      allPosts = allPosts.filter(function(post) {
        return postMatchesFilter(post, targetFilter);
      });
    }

    if (allPosts.length > 0) {
      window.renderPage(1);
    } else if (targetFilter) {
      var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts, .tech-featured-grid');
      if (container) {
        container.innerHTML = '<div style="text-align:center;padding:4rem 1rem;color:#64748b;background:#fff;border-radius:12px;margin-bottom:2rem;">' +
          '<h3 style="font-size:1.25rem;font-weight:600;margin-bottom:0.5rem;color:#1e293b;">해당 카테고리의 포스팅이 없습니다</h3>' +
          '<p style="font-size:0.95rem;">카테고리 라벨: "' + targetFilter + '"</p></div>';
      }
    }
  };

  // =========================================================
  // 8. Category Modal Engine
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
      if (e.target === modalDiv) window.closeCategoriesModal();
    });
    return modalDiv;
  }

  window.showCategoriesModal = function() {
    var modal = ensureCategoriesModalExists();
    if (!modal) return;
    if (modal.parentElement !== document.body) document.body.appendChild(modal);

    var modalContainer = document.getElementById('modal-tags-container');
    if (!modalContainer) return;

    if (!currentTagsData || currentTagsData.length === 0) {
      var widget = document.getElementById('Label1') || document.querySelector('.widget.Label') || document.querySelector('[id^="Label"]');
      if (widget) {
        var anchors = Array.from((widget.querySelector('.widget-content') || widget).querySelectorAll('a'));
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
      var name = rawText, count = '';
      var match = rawText.match(/(.+?)\s*\((\d+)\)$/);
      if (match) { name = match[1].trim(); count = match[2]; }
      tagsData.push({ name: name, count: count, url: a.getAttribute('href') });
    });

    if (tagsData.length === 0) return;
    tagsData.sort(function(a, b) {
      var countA = a.count ? parseInt(a.count, 10) : 0;
      var countB = b.count ? parseInt(b.count, 10) : 0;
      if (countA !== countB) return countB - countA;
      return a.name.localeCompare(b.name, 'ko', { sensitivity: 'base' });
    });

    currentTagsData = tagsData;
    container.innerHTML = '';
    var tagsBox = document.createElement('div');
    tagsBox.className = 'devlog-tags';
    container.appendChild(tagsBox);

    tagsData.forEach(function(tag, idx) {
      if (idx < 8) {
        var tagEl = document.createElement('a');
        tagEl.href = tag.url;
        tagEl.className = 'tech-tag';
        tagEl.textContent = tag.name;
        if (tag.count) {
          var cEl = document.createElement('span');
          cEl.className = 'label-count';
          cEl.style.cssText = 'margin-left:4px;font-weight:700;color:var(--primary-color, #2563eb);';
          cEl.textContent = '(' + tag.count + ')';
          tagEl.appendChild(cEl);
        }
        tagsBox.appendChild(tagEl);
      }
    });

    if (tagsData.length > 8) {
      var moreBtn = document.createElement('button');
      moreBtn.type = 'button';
      moreBtn.className = 'tech-tag-more-btn';
      moreBtn.id = 'tech-tag-more-btn';
      moreBtn.textContent = '...';
      moreBtn.onclick = function(e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        window.showCategoriesModal();
        return false;
      };
      tagsBox.appendChild(moreBtn);
    }
  }

  function enforceInitial4CardGrid() {
    var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts, .tech-featured-grid');
    if (!container || allPosts.length > 0) return;

    var cards = Array.from(container.children).filter(function(child) {
      return child.classList.contains('post-card') || child.classList.contains('tech-post-card') || child.tagName === 'ARTICLE';
    });

    for (var i = postPerPage; i < cards.length; i++) {
      cards[i].style.display = 'none';
    }
  }

  // =========================================================
  // 9. DOMContentLoaded Init
  // =========================================================
  document.addEventListener('DOMContentLoaded', function() {
    ensureCategoriesModalExists();
    initCategoryTagsLimit();
    enforceInitial4CardGrid();
    setTimeout(enforceInitial4CardGrid, 300);

    // 개별 포스트 페이지가 아닌 경우에만 피드 로드
    var isPostPage = window.location.pathname.indexOf('/20') === 0 && window.location.pathname.indexOf('.html') !== -1;
    if (!isPostPage) {
      var script = document.createElement('script');
      script.src = '/feeds/posts/summary?alt=json-in-script&max-results=150&callback=initBloggerFeedPagination';
      document.body.appendChild(script);
    }

    // Mermaid
    var mermaidEls = document.querySelectorAll('.mermaid');
    if (mermaidEls.length > 0 && typeof mermaid !== 'undefined') {
      mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose', flowchart: { useMaxWidth: true, htmlLabels: true } });
    }
  });

  // Global click delegation for modal more button
  document.addEventListener('click', function(e) {
    var target = e.target;
    if (target && (target.classList.contains('tech-tag-more-btn') || target.id === 'tech-tag-more-btn')) {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      window.showCategoriesModal();
      return false;
    }
  }, true);

})();
