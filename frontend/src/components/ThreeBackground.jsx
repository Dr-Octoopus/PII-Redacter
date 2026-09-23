import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeBackground({ theme = 'dark' }) {
  const containerRef = useRef(null);
  const themeRef = useRef(theme);

  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  useEffect(() => {
    if (!containerRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      55,
      window.innerWidth / window.innerHeight,
      1,
      2000
    );
    camera.position.set(0, 0, 450);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    containerRef.current.appendChild(renderer.domElement);

    // Theme Color Palettes
    const palettes = {
      dark: {
        coreColor: 0x6366f1,
        innerCoreColor: 0x818cf8,
        particleColor: 0x818cf8,
        lineColor: 0x6366f1,
        ringColor: 0xc084fc,
        lineOpacity: 0.18,
      },
      light: {
        coreColor: 0x4f46e5,
        innerCoreColor: 0x7c3aed,
        particleColor: 0x3b82f6,
        lineColor: 0x4f46e5,
        ringColor: 0x9333ea,
        lineOpacity: 0.14,
      }
    };

    let currentColors = themeRef.current === 'light' ? palettes.light : palettes.dark;

    // 1. Central Holographic Cyber Core (Outer Icosahedron Wireframe)
    const coreGeo = new THREE.IcosahedronGeometry(90, 1);
    const coreMat = new THREE.MeshBasicMaterial({
      color: currentColors.coreColor,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    scene.add(coreMesh);

    // Inner Glowing Core (Octahedron Wireframe)
    const innerGeo = new THREE.OctahedronGeometry(50, 0);
    const innerMat = new THREE.MeshBasicMaterial({
      color: currentColors.innerCoreColor,
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    scene.add(innerMesh);

    // Orbiting Cyber Ring (Torus)
    const ringGeo = new THREE.TorusGeometry(140, 0.8, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({
      color: currentColors.ringColor,
      transparent: true,
      opacity: 0.25,
      wireframe: true,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 3;
    scene.add(ringMesh);

    // Second Orbiting Ring
    const ring2Geo = new THREE.TorusGeometry(170, 0.5, 12, 90);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: currentColors.coreColor,
      transparent: true,
      opacity: 0.18,
      wireframe: true,
    });
    const ring2Mesh = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2Mesh.rotation.y = Math.PI / 4;
    scene.add(ring2Mesh);

    // 2. Floating 3D Node Constellation Grid
    const particleCount = 140;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const velocities = [];

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 900;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 900;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 500;

      velocities.push({
        x: (Math.random() - 0.5) * 0.45,
        y: (Math.random() - 0.5) * 0.45,
        z: (Math.random() - 0.5) * 0.25,
      });
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: currentColors.particleColor,
      size: 4,
      transparent: true,
      opacity: 0.75,
    });

    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // 3. Dynamic Connecting Lines
    const lineMat = new THREE.LineBasicMaterial({
      color: currentColors.lineColor,
      transparent: true,
      opacity: currentColors.lineOpacity,
    });

    const lineGeo = new THREE.BufferGeometry();
    const lineMesh = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lineMesh);

    // Mouse Interaction Variables
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (event) => {
      mouseX = (event.clientX - window.innerWidth / 2);
      mouseY = (event.clientY - window.innerHeight / 2);
    };

    window.addEventListener('mousemove', handleMouseMove);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    // Animation Loop
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Check for dynamic theme palette changes
      const activeTheme = themeRef.current;
      const targetColors = activeTheme === 'light' ? palettes.light : palettes.dark;

      coreMat.color.setHex(targetColors.coreColor);
      innerMat.color.setHex(targetColors.innerCoreColor);
      ringMat.color.setHex(targetColors.ringColor);
      ring2Mat.color.setHex(targetColors.coreColor);
      particleMat.color.setHex(targetColors.particleColor);
      lineMat.color.setHex(targetColors.lineColor);
      lineMat.opacity = targetColors.lineOpacity;

      // 1. Rotate Cyber Core meshes organically
      coreMesh.rotation.x = elapsedTime * 0.15;
      coreMesh.rotation.y = elapsedTime * 0.2;

      innerMesh.rotation.x = -elapsedTime * 0.3;
      innerMesh.rotation.z = elapsedTime * 0.25;

      ringMesh.rotation.z = elapsedTime * 0.1;
      ring2Mesh.rotation.x = elapsedTime * 0.08;

      // Pulse core scale slightly
      const pulseScale = 1 + Math.sin(elapsedTime * 1.5) * 0.05;
      coreMesh.scale.set(pulseScale, pulseScale, pulseScale);

      // 2. Animate particles and rebuild connecting lines
      const posAttr = particleGeo.attributes.position;
      const posArr = posAttr.array;
      const linePositions = [];

      for (let i = 0; i < particleCount; i++) {
        posArr[i * 3] += velocities[i].x;
        posArr[i * 3 + 1] += velocities[i].y;
        posArr[i * 3 + 2] += velocities[i].z;

        // Boundary bounce
        if (Math.abs(posArr[i * 3]) > 450) velocities[i].x *= -1;
        if (Math.abs(posArr[i * 3 + 1]) > 450) velocities[i].y *= -1;
        if (Math.abs(posArr[i * 3 + 2]) > 250) velocities[i].z *= -1;

        // Distance connections
        for (let j = i + 1; j < particleCount; j++) {
          const dx = posArr[i * 3] - posArr[j * 3];
          const dy = posArr[i * 3 + 1] - posArr[j * 3 + 1];
          const dz = posArr[i * 3 + 2] - posArr[j * 3 + 2];
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

          if (dist < 125) {
            linePositions.push(
              posArr[i * 3], posArr[i * 3 + 1], posArr[i * 3 + 2],
              posArr[j * 3], posArr[j * 3 + 1], posArr[j * 3 + 2]
            );
          }
        }
      }

      posAttr.needsUpdate = true;
      lineGeo.setAttribute(
        'position',
        new THREE.Float32BufferAttribute(linePositions, 3)
      );

      // 3. Smooth Mouse Parallax Physics
      targetX = mouseX * 0.25;
      targetY = mouseY * 0.25;

      camera.position.x += (targetX - camera.position.x) * 0.04;
      camera.position.y += (-targetY - camera.position.y) * 0.04;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
      }}
    />
  );
}
