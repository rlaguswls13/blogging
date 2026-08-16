/**
 * TECH LOG - Unified Site Theme JS Engine (v2.3.0)
 * Fixed Modal Toggle Engine (Default Hidden, Guaranteed Close)
 */
(function() {
  'use strict';

  // =========================================================
  // 1. Dynamic Category Modal Injector & 12-Tag Limit Engine
  // =========================================================
  function ensureCategoriesModalExists() {
    var existingModal = document.getElementById('categories-modal');
    if (existingModal) {
      existingModal.style.setProperty('display', 'none', 'important');
      return;
    }

    var modalDiv = document.createElement('div');
    modalDiv.id = 'categories-modal';
    modalDiv.className = 'modal-overlay';
    modalDiv.setAttribute('style', 'display: none !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(15, 23, 42, 0.5) !important; backdrop-filter: blur(4px) !important; align-items: center !important; justify-content: center !important; z-index: 99999 !important; padding: 1rem !important;');
    modalDiv.innerHTML = 
      '<div class="modal-box">' +
        '<div class="modal-header">' +
          '<h3>전체 카테고리</h3>' +
          '<button class="modal-close-btn" id="modal-close-btn-x" type="button">×</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<div class="devlog-tags-popup" id="modal-tags-container"></div>' +
        '</div>' +
      '</div>';
    
    document.body.appendChild(modalDiv);

    var closeBtn = document.getElementById('modal-close-btn-x');
    if (closeBtn) {
      closeBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        closeCategoriesModal();
      });
    }

    modalDiv.addEventListener('click', function(e) {
      if (e.target === modalDiv) {
        closeCategoriesModal();
      }
    });
  }

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

    // 기존 내용 비우고 모던 devlog-tags 칩 박스로 렌더링
    container.innerHTML = '';
    var tagsBox = document.createElement('div');
    tagsBox.className = 'devlog-tags';
    container.appendChild(tagsBox);

    // 상위 12개 렌더링
    tagsData.forEach(function(tag, idx) {
      if (idx < 12) {
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

    // 12개 초과 시 '...' 모달 더보기 버튼 렌더링 (13번째 위치)
    if (tagsData.length > 12) {
      var moreBtn = document.createElement('button');
      moreBtn.type = 'button';
      moreBtn.className = 'tech-tag-more-btn';
      moreBtn.textContent = '...';
      
      moreBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        showAllCategoriesModal(tagsData);
      });
      tagsBox.appendChild(moreBtn);
    }
  }

  function showAllCategoriesModal(tagsData) {
    ensureCategoriesModalExists();
    var modal = document.getElementById('categories-modal');
    var modalContainer = document.getElementById('modal-tags-container');
    if (!modal || !modalContainer) return;

    modalContainer.innerHTML = '';
    var tags = tagsData || [];

    tags.forEach(function(tag) {
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

    modal.style.setProperty('display', 'flex', 'important');
    document.body.style.overflow = 'hidden';
  }

  function closeCategoriesModal() {
    var modal = document.getElementById('categories-modal');
    if (modal) {
      modal.style.setProperty('display', 'none', 'important');
      document.body.style.overflow = '';
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

    if (allPosts.length > 0) {
      renderPage(1);
    }
  };

  // =========================================================
  // 3. Event Listeners and Initialization
  // =========================================================
  document.addEventListener("DOMContentLoaded", function() {
    ensureCategoriesModalExists();
    initCategoryTagsLimit();
    enforceInitial4CardGrid();

    setTimeout(function() {
      initCategoryTagsLimit();
      enforceInitial4CardGrid();
    }, 300);

    setTimeout(function() {
      initCategoryTagsLimit();
      enforceInitial4CardGrid();
    }, 1000);

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

  window.addEventListener('click', function(e) {
    var modal = document.getElementById('categories-modal');
    if (e.target === modal) {
      closeCategoriesModal();
    }
  });

})();
